"""Verify private generated intermediates before reusing a recovery checkpoint."""
import hashlib
import json
from pathlib import Path

REUSABLE = (
    'extract_programs.py', 'convert_programs.py', 'extract_compute_meta.py',
    'extract_all_shader_meta.py', 'dump_shader_parameters.py',
    'shader_parameter_parser.py',
)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def artifact_paths(workspace, script):
    workspace = Path(workspace).resolve()
    runtime = workspace/'work/dsp-runtime'
    batch = workspace/'work/dsp-shader-probe/batch'
    def read(path):
        return json.loads(path.read_text())
    if script == 'extract_programs.py':
        manifest = batch/'inventory.json'; data = read(manifest)
        if data.get('errors') or not data.get('programs'):
            raise ValueError('Program inventory is incomplete')
        paths = [manifest] + [batch/'programs'/(row['sha256']+'.dxbc') for row in data['programs']]
    elif script == 'convert_programs.py':
        manifest = batch/'spirv-results.json'; rows = read(manifest)
        expected = {row['sha256'] for row in read(batch/'inventory.json')['programs']}
        if not rows or any(row['returncode'] for row in rows) or {row['sha256'] for row in rows} != expected:
            raise ValueError('SPIR-V conversion results are incomplete')
        paths = [manifest] + [batch/'programs'/(sha+'.spv') for sha in sorted(expected)]
    elif script == 'extract_compute_meta.py':
        manifest = runtime/'compute-metadata.json'
        if len(read(manifest)) != 19:
            raise ValueError('Expected 19 compute shader records')
        paths = [manifest]
    elif script == 'extract_all_shader_meta.py':
        manifest = runtime/'graphics-metadata/index.json'; rows = read(manifest)
        if not rows:
            raise ValueError('Shader metadata inventory is empty')
        paths = [manifest] + [workspace/row['path'] for row in rows]
    elif script == 'dump_shader_parameters.py':
        paths = list((runtime/'graphics-parameters').glob('*.bin'))
        if not paths:
            raise ValueError('Shader parameter files are missing')
    elif script == 'shader_parameter_parser.py':
        manifest = runtime/'graphics-parameters/parsed.json'; data = read(manifest)
        if not data or any(not (manifest.parent/key).is_file() for key in data):
            raise ValueError('Parsed shader parameters are incomplete')
        paths = [manifest]
    else:
        raise ValueError('Unknown reusable stage: '+script)
    result = []
    for path in paths:
        path = path.resolve()
        if workspace not in path.parents or not path.is_file() or path.stat().st_size == 0:
            raise ValueError('Missing or invalid recovery artifact: '+str(path))
        result.append(path)
    return sorted(set(result))

def capture(workspace, script, script_hash):
    workspace = Path(workspace).resolve()
    return {'schema': 1, 'scriptSha256': script_hash, 'artifacts': {
        str(path.relative_to(workspace)): digest(path)
        for path in artifact_paths(workspace, script)
    }}

def reusable(workspace, script, script_hash, saved):
    # Older script-only checkpoints cannot prove that their outputs survived.
    if not isinstance(saved, dict) or saved.get('schema') != 1 or saved.get('scriptSha256') != script_hash:
        return False
    try:
        return capture(workspace, script, script_hash) == saved
    except (OSError, ValueError, KeyError, TypeError):
        return False

def invalidate_following(completed, script):
    for later in REUSABLE[REUSABLE.index(script):]:
        completed.pop(later, None)


def verify_dependencies(state):
    # A replaced converter binary can invalidate cached HLSL without changing a
    # Python script. Keep the workspace tied to the tools recorded at prepare.
    for label in ('spirvCross', 'vkd3d'):
        entry = state.get('dependencies', {}).get(label)
        if not entry or digest(entry['path']) != entry['sha256']:
            raise ValueError('Recovery dependency missing or changed: '+label+
                             '. Restore the originally selected binary or prepare a new private workspace.')
