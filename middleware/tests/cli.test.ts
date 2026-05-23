import { describe, it, expect } from 'vitest';
import { parseArgs, CliCommand } from '../src/cli';

describe('parseArgs', () => {
    it('returns "run" command by default', () => {
        expect(parseArgs([])).toEqual({ command: 'run' });
    });

    it('parses install-hook subcommand', () => {
        expect(parseArgs(['install-hook'])).toEqual({ command: 'install-hook' });
    });

    it('parses uninstall subcommand', () => {
        expect(parseArgs(['uninstall'])).toEqual({ command: 'uninstall' });
    });

    it('parses --version', () => {
        expect(parseArgs(['--version'])).toEqual({ command: 'version' });
    });

    it('parses --help', () => {
        expect(parseArgs(['--help'])).toEqual({ command: 'help' });
        expect(parseArgs(['-h'])).toEqual({ command: 'help' });
    });

    it('respects AEGIS_INSTALL_HOOK=0 env to skip consent', () => {
        const args = parseArgs([], { AEGIS_INSTALL_HOOK: '0' });
        expect(args).toEqual({ command: 'run', skipHookInstall: true });
    });

    it('respects AEGIS_INSTALL_HOOK=1 env to auto-consent', () => {
        const args = parseArgs([], { AEGIS_INSTALL_HOOK: '1' });
        expect(args).toEqual({ command: 'run', autoConsent: true });
    });
});
