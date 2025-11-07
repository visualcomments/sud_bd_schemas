import argparse, json, os, sys
from jsonschema import Draft202012Validator

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_dir(schema_dir, example_path=None):
    schemas = {}
    for fn in os.listdir(schema_dir):
        if fn.endswith('.json'):
            p = os.path.join(schema_dir, fn)
            with open(p, 'r', encoding='utf-8') as f:
                schemas[fn] = json.load(f)
    # Pre-build validators
    validators = {name: Draft202012Validator(sch) for name, sch in schemas.items()}
    print(f"Loaded {len(validators)} schema(s)")
    if example_path:
        data = load_json(example_path)
        # try to detect by $id in example or require explicit mapping
        for name, validator in validators.items():
            try:
                validator.validate(data)
                print(f"Example {os.path.basename(example_path)} is valid for {name}")
            except Exception as e:
                pass

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True, help='Folder with JSON Schemas')
    ap.add_argument('--example', help='Optional example JSON to validate')
    args = ap.parse_args()
    validate_dir(args.dir, args.example)
