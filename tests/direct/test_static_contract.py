from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "filing_trigger_covenant.py"


def test_contract_file_exists():
    assert CONTRACT.exists()


def test_contract_is_ascii():
    data = CONTRACT.read_bytes()
    data.decode("ascii")


def test_contract_header_shape():
    lines = CONTRACT.read_text(encoding="ascii").splitlines()
    assert lines[0].startswith("# v")
    assert lines[1].startswith('# { "Depends": "py-genlayer:')
    assert lines[2] == "from genlayer import *"


def test_contract_declares_schema_constructor():
    tree = ast.parse(CONTRACT.read_text(encoding="ascii"))
    contract_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Contract"
    )
    init = next(
        (
            node
            for node in contract_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        ),
        None,
    )

    assert init is not None
    assert len(init.args.args) == 1
    assert init.args.args[0].arg == "self"


def test_no_frontend_directory():
    assert not (ROOT / "frontend").exists()
