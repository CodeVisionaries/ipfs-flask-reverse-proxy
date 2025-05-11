### Reverse Proxy for selective Kubo IPFS RPC exposure 

The [IPFS Kubo client](https://docs.ipfs.tech/install/command-line/) comes with a
[RPC API](https://docs.ipfs.tech/reference/kubo/rpc/) to perform various actions,
such as adding and retrieving files from the Interplanetary File System (IPFS).
However, this API should never be exposed to the public as it gives full management
control over the IPFS node.

Not everyone will have the possibility or willingness to set up an IPFS node themself
but it may still be beneficial if everyone has the opportunity to upload (and thereby share)
relevant files, such as new nuclear data evaluations).

A possible solution is to put a reverse proxy, accessible by the public, in front of
the Kubo RPC API. The proxy only forwards white-listed API calls and blocks the rest.

As a proof-of-concept, this flask application implements such a reverse proxy
for adding (and pinning) files on the IPFS node if the file is of a certain type.
In this POC, a file is only accepted if it is an ENDF file, an ENDF file in JSON format,
a [JsonGraphNode](https://github.com/CodeVisionaries/jsontools/blob/d6ebfe8bba889f0c64735cfd3c72ab10f84e7e25/src/jsontools/json/schemas/schema_json_graph_node_base_v0_0_1.json)
or
a [ExtJsonPatch](https://github.com/CodeVisionaries/jsontools/blob/d6ebfe8bba889f0c64735cfd3c72ab10f84e7e25/src/jsontools/json/schemas/schema_ext_json_patch_base_v0_0_1.json).


## Installation

This flask application uses the Kubo RPC API so you need to
[install the Kubo IPFS client](https://docs.ipfs.tech/install/command-line/).

```
git clone https://github.com/CodeVisionaries/ipfs-flask-reverse-proxy
git clone https://github.com/CodeVisionaries/jsonvc
python -m venv venv
source venv/bin/activate
pip install flask requests endf_parserpy orjson
pip install ./jsonvc
pip install ./ipfs-flask-reverse-proxy
```

## Usage

Before you run the IPFS Kubo client for the first time, initialize the local node cache:
```
ipfs init
```
Start the IPFS Kubo client:
```
ipfs daemon
```

Switch to another terminal window and change into the `ipfs-flask-reverse-proxy` directory.
Activate the virtual environment:
```
source venv/bin/activate
```
Start the flask application:
```
python app/ipfs_gateway.py
```

Now you can add files of valid type (e.g. ENDF, see above) via
```
curl -X POST -F "file=@/path/to/file" http://127.0.0.1:5000/ipfs-api-relay/v0/add
```
If the upload is successful, the [content id](https://docs.ipfs.tech/concepts/content-addressing/) (CID)
and status message will be returned, e.g.
```
{
    "Name":"n_2625_26-Fe-54.json",
    "Hash":"QmdQuzmstKuhxyoDPGcEUeouJxdeNfjNCwCBJDE7dTjsix",
    "Size":"43042661"
}
```
