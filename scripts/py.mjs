// Use the project environment without shell-specific path syntax.
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const python = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const child = spawn(python, process.argv.slice(2), {cwd: root, stdio: 'inherit'});
child.on('error', error => {
  console.error(`Cannot start Engineering Workshop's Python: ${error.message}. Run setup first; see README.md.`);
  process.exitCode = 1;
});
child.on('exit', (code, signal) => {
  process.exitCode = code ?? (signal ? 1 : 0);
});
