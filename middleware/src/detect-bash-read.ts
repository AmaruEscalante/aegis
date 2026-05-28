// ============================================================================
// detect-bash-read — classify a Bash command as a simple single-file read
// ============================================================================
// Pure, dependency-light helper used by the Aegis PreToolUse hook to decide
// whether a Bash command should be redirected to aegis_read. Cooperative
// threat model: catch the habitual single-file reads (cat/head/grep FILE) and
// FAIL OPEN on anything ambiguous (pipes-with-substitution, redirection,
// chaining, multiple files, indirect interpreters). See
// docs/superpowers/specs/2026-05-28-phase-5-bash-enforcement-design.md.

import { parse } from 'shell-quote';

export type BashReadResult = { isRead: true; path: string } | { isRead: false };

// Read their single file argument directly.
const ALWAYS_READERS = new Set([
  'cat', 'bat', 'head', 'tail', 'less', 'more', 'nl', 'tac',
  'od', 'xxd', 'hexdump', 'strings', 'base64', 'base32', 'cut', 'fold',
]);

// Take a pattern/script first, then read trailing file args.
const PATTERN_READERS = new Set(['grep', 'egrep', 'fgrep', 'rg', 'sed', 'awk']);

// Short/long flags that consume the NEXT token as their value (for ALWAYS
// readers — head/tail/cut). Used so `head -n 5 file` counts `file`, not `5`.
// KNOWN LIMITATION: this set is shared across all ALWAYS_READERS, so a flag
// that takes a value for one command (e.g. `-f` = field for `cut`) but is
// boolean for another (e.g. `-f` = follow for `tail`) over-skips the next
// token — so `tail -f app.log` fails open (under-blocks). Acceptable under the
// cooperative fail-open design.
const VALUE_FLAGS = new Set(['-n', '-c', '-d', '-f', '--lines', '--bytes']);

// Operators that delimit the first command segment of a pipeline/chain.
const SEGMENT_DELIMITERS = new Set(['|', '&&', '||', ';']);

export function detectBashRead(command: string): BashReadResult {
  let tokens: ReturnType<typeof parse>;
  try {
    tokens = parse(command);
  } catch {
    return { isRead: false }; // parse failure → fail open
  }

  // Collect the first segment (up to the first pipe/chain delimiter).
  const firstSegment: typeof tokens = [];
  for (const tok of tokens) {
    if (
      typeof tok === 'object' &&
      tok !== null &&
      'op' in tok &&
      SEGMENT_DELIMITERS.has((tok as { op: string }).op)
    ) {
      break;
    }
    firstSegment.push(tok);
  }

  // Any non-string token in the first segment (operator, glob, comment,
  // command substitution, redirection) means shell complexity → fail open.
  for (const tok of firstSegment) {
    if (typeof tok !== 'string') return { isRead: false };
  }
  const strs = firstSegment as string[];
  if (strs.length === 0) return { isRead: false };

  // basename so /bin/cat matches cat
  const cmd = strs[0].split('/').pop() ?? strs[0];
  const args = strs.slice(1);

  if (ALWAYS_READERS.has(cmd)) {
    const files: string[] = [];
    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a.startsWith('-')) {
        if (VALUE_FLAGS.has(a)) i++; // skip this flag's value token
        continue; // option (boolean, attached-value like -n5, or --x=y)
      }
      files.push(a);
    }
    if (files.length === 1) return { isRead: true, path: files[0] };
    return { isRead: false }; // stdin (0) or multiple files → fail open
  }

  if (PATTERN_READERS.has(cmd)) {
    // Treat every '-' token as a standalone boolean option (don't skip a
    // following value): pattern-reader value-flags are command-specific.
    const nonOptions = args.filter((a) => !a.startsWith('-'));
    // nonOptions[0] is the pattern/script; remaining are files.
    // INTENTIONAL ASYMMETRY: unlike ALWAYS_READERS (which fail open on multiple
    // files), PATTERN_READERS with multiple files return the LAST file as the
    // path — grepping multiple files is common, and gating one file the command
    // touches is still useful.
    if (nonOptions.length >= 2) {
      return { isRead: true, path: nonOptions[nonOptions.length - 1] };
    }
    return { isRead: false };
  }

  return { isRead: false };
}
