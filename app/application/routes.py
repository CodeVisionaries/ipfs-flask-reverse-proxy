from flask import current_app as app
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import requests
import json
from endf_parserpy import EndfParserCpp
from jsontools.json.models import JsonGraphNode, ExtJsonPatch
from endf_parserpy import sanitize_fieldname_types

IPFS_URL = 'http://127.0.0.1:5001/api/v0/add'


def is_json_graph_node(json_dict):
    try:
        JsonGraphNode(**json_dict)
        return True
    except:
        return False


def is_ext_json_patch(json_dict):
    try:
        ExtJsonPatch(**json_dict)
        return True
    except:
        return False


def is_json_endf(json_dict):
    try:
        sanitize_fieldname_types(json_dict)
        parser = EndfParserCpp()
        parser.write(json_dict)
        return True
    except:
        return False


def is_allowed_json(objstr):
    try:
        json_dict = json.loads(objstr)
    except:
        return False
    if is_json_graph_node(json_dict):
        return True
    if is_ext_json_patch(json_dict):
        return True
    # is_json_endf comes last because it
    # modifies the json_dict so it can be
    # understood by endf_parserpy (keys containing
    # integers are converted to datatype integer)
    if is_json_endf(json_dict):
        return True
    return False


def is_endf(objstr):
    if '\n' not in objstr[:90]:
        # one-line strings may be interpreted as an
        # ENDF file with a TPID record only by the parser
        return False
    try:
        parser = EndfParserCpp()
        parser.parse(objstr)
        return True
    except:
        return False


def is_valid_file_content(file_content):
    if is_allowed_json(file_content):
        return True
    if is_endf(file_content):
        return True
    return False


@app.route('/ipfs/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    upload_file = request.files['file']
    filename = secure_filename(upload_file.filename)
    files = {'file': (filename, upload_file.stream, 'application/octet-stream')} 
    # add to IPFS
    file_content = upload_file.read().decode('utf-8')
    upload_file.seek(0)
    if is_valid_file_content(file_content):
        pass
    else:
        return jsonify({'error': 'Invalid file (must be ENDF, ENDF-JSON or a JSON file with JsonGraphNode or ExtJsonPatch structure'}), 500
    # if successful do, add to ipfs
    try:
        response = requests.post(IPFS_URL, files=files)
        response.raise_for_status()
        ipfs_hash = response.json()['Hash']
        return jsonify({'message': 'File uploaded successfully to IPFS', 'ipfs_hash': ipfs_hash}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Error uploading to IPFS: {str(e)}'}), 500
