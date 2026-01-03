import grpc
import csv
import gzip
import re
from concurrent import futures
import PropertyLookup_pb2
import PropertyLookup_pb2_grpc

class PropertyLookupService(PropertyLookup_pb2_grpc.PropertyLookupServicer):
    def __init__(self):
        self.address_data = self.load_addresses()

    def load_addresses(self):
        addresses = {}
        with gzip.open("addresses.csv.gz", "rt") as f:
            reader = csv.reader(f)
            next(reader)  
            for row in reader:
                zip_code = row[11].strip() 
                address = row[9].strip()  
                if zip_code not in addresses:
                    addresses[zip_code] = []
                addresses[zip_code].append(address)

        return addresses

    def natural_sort_key(self, address):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', address)]

    def LookupByZip(self, request, context):
        zip_code = str(request.zip)
        limit = request.limit

        addresses = sorted(self.address_data.get(zip_code, []), key=self.natural_sort_key)

        return PropertyLookup_pb2.AddressList(addresses=addresses[:limit])

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    PropertyLookup_pb2_grpc.add_PropertyLookupServicer_to_server(PropertyLookupService(), server)
    server.add_insecure_port("0.0.0.0:5000")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
