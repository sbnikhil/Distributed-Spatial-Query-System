import flask
import grpc
import os
import time
import itertools
from flask import Flask, jsonify, request
from PropertyLookup_pb2 import ZipRequest
from PropertyLookup_pb2_grpc import PropertyLookupStub
from collections import OrderedDict

app = Flask("p2")

class LRUCache(OrderedDict):
    def __init__(self, capacity=3):
        super().__init__()
        self.capacity = capacity

    def get(self, key):
        if key in self:
            self.move_to_end(key)
            return self[key]
        return None

    def put(self, key, value):
        if key in self:
            self.move_to_end(key)
        elif len(self) >= self.capacity:
            self.popitem(last=False)
        self[key] = value

cache = LRUCache(3)
PROJECT = os.getenv("PROJECT", "p2")
DATASET_SERVERS = [f"{PROJECT}-dataset-1:5000", f"{PROJECT}-dataset-2:5000"]
server_selector = itertools.cycle(DATASET_SERVERS)

def get_addresses(zipcode, limit):
    attempts = 5
    for attempt in range(attempts):
        dataset_server = next(server_selector)
        try:
            with grpc.insecure_channel(dataset_server) as channel:
                stub = PropertyLookupStub(channel)
                request_limit = max(8, limit)  # Request at least 8, or limit if larger
                response = stub.LookupByZip(ZipRequest(zip=zipcode, limit=request_limit))
                sorted_addresses = sorted(response.addresses, key=lambda addr: addr.lower())
                return sorted_addresses, "1" if "dataset-1" in dataset_server else "2"
        except grpc.RpcError as e:
            print(f" gRPC error from {dataset_server} (Attempt {attempt+1}/{attempts}): {e}")
            time.sleep(0.1)
            continue
    return [], None

@app.route("/lookup/<zipcode>")
def lookup(zipcode):
    zipcode = int(zipcode)
    limit = request.args.get("limit", default=4, type=int)

    cached_data = cache.get(zipcode)
    if cached_data and limit <= 8:
        return jsonify({"addrs": cached_data[:limit], "source": "cache", "error": None})

    addresses, source = get_addresses(zipcode, limit)

    if addresses:
        cache.put(zipcode, addresses[:8])  # Always cache the first 8 (or fewer)
        return jsonify({"addrs": addresses[:limit], "source": source, "error": None})

    cached_data = cache.get(zipcode)
    if cached_data:
        return jsonify({"addrs": cached_data[:limit], "source": "cache", "error": "Dataset servers unavailable"})

    return jsonify({"addrs": [], "source": None, "error": "All dataset servers failed after 5 retries"}), 503

def main():
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=False)

if __name__ == "__main__":
    main()
