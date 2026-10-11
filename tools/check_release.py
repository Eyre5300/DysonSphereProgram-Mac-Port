"""Conservative release boundary check, including untracked files. No uploads."""
from pathlib import Path
import sys
ALLOWED={'.command','.py','.cs','.c','.h','.sh','.json','.md','.txt','.toml','.yml','.yaml'}
PRIVATE={'local-private','Assembly-CSharp','Library','StreamingAssets','Resources','private-fixtures'}
def check_release(root):
 root=Path(root); paths=[]; failures=[]
 for p in sorted(root.rglob('*')):
  relative=p.relative_to(root)
  if any(part in {'.git','__pycache__'} for part in relative.parts) or p.name=='.DS_Store':continue
  if not p.is_file() and not p.is_symlink():continue
  name=str(relative); paths.append(name)
  if p.is_symlink():
   failures.append((name,'symlink'));continue
  if p.suffix not in ALLOWED and p.name not in {'.gitignore','LICENSE'}:failures.append((name,'unexpected file type'))
  if p.stat().st_size>250_000:failures.append((name,'large file requires review'))
  if any(part in PRIVATE for part in relative.parts):failures.append((name,'private/game path'))
  if p.suffix in ALLOWED:
   content=p.read_text(errors='replace')
   if ('/'+'Users'+'/') in content or ('steamapps'+'/content/') in content:failures.append((name,'machine-specific path'))
 return paths,failures
if __name__=='__main__':
 paths,failures=check_release(Path(__file__).resolve().parents[1])
 print('FAIL' if failures else 'PASS',len(paths),'files checked; manual source-origin review still required')
 for name,why in failures:print(name,why)
 sys.exit(bool(failures))
