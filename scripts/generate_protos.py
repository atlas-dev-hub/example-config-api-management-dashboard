"""Generate Python gRPC stubs from proto files.

Run from the project root:
    python scripts/generate_protos.py
"""

import subprocess
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parent.parent
    proto_dir = project_root / "protos"
    output_dir = project_root / "sm_config_api" / "generated"

    output_dir.mkdir(parents=True, exist_ok=True)

    proto_files = sorted(proto_dir.glob("*.proto"))
    if not proto_files:
        print(f"ERROR: No .proto files found in {proto_dir}")
        sys.exit(1)

    print(f"Proto dir:   {proto_dir}")
    print(f"Output dir:  {output_dir}")
    print(f"Proto files: {[f.name for f in proto_files]}")
    print()

    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"--proto_path={proto_dir}",
        f"--python_out={output_dir}",
        f"--pyi_out={output_dir}",
        f"--grpc_python_out={output_dir}",
    ] + [str(f) for f in proto_files]

    print(f"Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"ERROR: protoc exited with code {result.returncode}")
        sys.exit(result.returncode)

    # Fix relative imports in generated files.
    # grpc_tools generates `import system_monitor_common_pb2 as ...`
    # but we need `from . import system_monitor_common_pb2 as ...` for package imports.
    generated_files = list(output_dir.glob("*.py"))
    fix_count = 0
    for gf in generated_files:
        content = gf.read_text(encoding="utf-8")
        original = content

        # Fix: `import system_monitor_common_pb2` → `from . import system_monitor_common_pb2`
        # but don't touch lines that already have `from .` or `from google`
        lines = content.split("\n")
        fixed_lines = []
        for line in lines:
            if (
                line.startswith("import system_monitor_")
                and "_pb2" in line
                and not line.startswith("from ")
            ):
                fixed_lines.append(f"from . {line}")
            else:
                fixed_lines.append(line)
        content = "\n".join(fixed_lines)

        if content != original:
            gf.write_text(content, encoding="utf-8")
            fix_count += 1

    print(f"Generated {len(generated_files)} files in {output_dir}")
    print(f"Fixed relative imports in {fix_count} files")

    # Verify __init__.py exists
    init_file = output_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text(
            '"""Auto-generated gRPC stubs for System Monitor Configuration API."""\n',
            encoding="utf-8",
        )
        print(f"Created {init_file}")

    print("\nDone!")


if __name__ == "__main__":
    main()
