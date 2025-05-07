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
    except:
        return False
    # trying both varities of JSON format,
    # see https://endf-parserpy.readthedocs.io/en/stable/guide/arrays_as_list.html
    try:
        parser = EndfParserCpp(array_type='dict')
        parser.write(json_dict)
        return True
    except:
        pass
    try:
        parser = EndfParserCpp(array_type='list')
        parser.write(json_dict)
        return True
    except:
        pass
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


def get_upload_file(request):
    if 'file' not in request.files:
        return None, {'error': 'No file part'}, 400
    return request.files['file'], {}, 200


def is_valid_file(upload_file):
    file_content = upload_file.read().decode('utf-8')
    upload_file.seek(0)
    if is_valid_file_content(file_content):
        pass
    else:
        return None, {'error': 'Invalid file (must be ENDF, ENDF-JSON or a JSON file with JsonGraphNode or ExtJsonPatch structure'}, 403
    return None, {}, 200


def invoke_ipfs_add(upload_file, params):
    filename = secure_filename(upload_file.filename)
    files = {'file': (filename, upload_file.stream, 'application/octet-stream')}
    try:
        response = requests.post(IPFS_URL, files=files, params=params)
        response.raise_for_status()
        ipfs_hash = response.json()['Hash']
        return ipfs_hash, {}, 200
    except requests.exceptions.RequestException as e:
        return None, jsonify({'error': f'Error uploading to IPFS: {str(e)}'}), 500


def ipfs_add_relay(request, params, custom_message):
    upload_file, message, status_code = get_upload_file(request)
    if status_code != 200:
        return jsonify(message), status_code
    _, message, status_code = is_valid_file(upload_file)
    if status_code != 200:
        return jsonify(message), status_code
    # if successful do, add to ipfs
    ipfs_hash, message, status_code = invoke_ipfs_add(upload_file, params)
    if status_code != 200:
        return jsonify(message), status_code
    return jsonify({'content_identifier': ipfs_hash, 'message': custom_message}), 200


@app.route('/ipfs/upload', methods=['POST'])
def upload_file():
    custom_message = 'File uploaded successfully to IPFS'
    return ipfs_add_relay(request, {}, custom_message)

@app.route('/ipfs/get-content-identifier', methods=['POST'])
def get_content_identifier():
    custom_message = 'Content Identifier (CID) successfully computed'
    return ipfs_add_relay(request, {'only-hash': True}, custom_message)
