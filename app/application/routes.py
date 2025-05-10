from flask import current_app as app
from flask import (
    Flask, request, jsonify, Response, stream_with_context
)
from werkzeug.utils import secure_filename
import requests
import json
from endf_parserpy import EndfParserCpp
from jsontools.json.models import JsonGraphNode, ExtJsonPatch
from endf_parserpy import sanitize_fieldname_types

IPFS_RPC_API_URL = 'http://127.0.0.1:5001/api'


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


def are_files_valid(request):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    for upload_file in request.files.getlist('file'):
        file_content = upload_file.read().decode('utf-8')
        upload_file.seek(0)
        if is_valid_file_content(file_content):
            pass
        else:
            return jsonify({'error': 'Invalid file (must be ENDF, ENDF-JSON or a JSON file with JsonGraphNode or ExtJsonPatch structure'}), 403
    return jsonify({'message': 'valid file'}), 200


def get_ipfs_add_post_args(request):
    # headers = {key: value for key, value in request.headers if key.lower() != 'host'}
    params = request.args.to_dict()
    files = [
        ('file', (secure_filename(file.filename), file.stream, file.content_type))
        for file in request.files.getlist('file')
    ]
    # return headers, params, files
    return params, files


def is_permissible_ipfs_add_request(request):
    params, files = get_ipfs_add_post_args(request)
    permitted_params = ['only-hash']
    if not all(k in permitted_params for k in params):
        return jsonify({'error': 'inadmissible parameters provided'}), 400
    permitted_file_keys = ['file']
    if not all(k[0] in permitted_file_keys for k in files):
        return jsonify({'error': 'inadmissible key(s) found in `files`'}), 400
    return are_files_valid(request)


def invoke_jailed_ipfs_add(request):
    message, status_code = is_permissible_ipfs_add_request(request)
    if status_code != 200:
        return message, status_code
    ipfs_api_add_url = IPFS_RPC_API_URL.rstrip('/') + '/v0/add'
    params, files = get_ipfs_add_post_args(request)
    try:
        response = requests.post(ipfs_api_add_url, params=params, files=files, stream=True)
        response.raise_for_status()
        return Response(
            stream_with_context(response.iter_content(chunk_size=10*1024)),
            status=response.status_code,
            headers=dict(response.headers)
        )
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Error uploading to IPFS: {str(e)}'}), 500


@app.route('/ipfs-api-relay/v0/add', methods=['POST'])
def ipfs_api_v0_add():
    return invoke_jailed_ipfs_add(request)
