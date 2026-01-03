# Distributed Spatial Query System

This repository contains a high-availability distributed system designed for querying Madison address data. The architecture utilizes gRPC for internal data retrieval and an HTTP/Flask gateway for external client access. The system is designed to handle node failures through replication and optimizes performance via a custom LRU caching layer.

## Architecture
The system is composed of five Docker containers orchestrated via Docker Compose:
* **Gateway Layer (3 Replicas):** Flask-based HTTP servers managing the caching logic and request routing.
* **Storage Layer (2 Replicas):** gRPC servers handling spatial data from `addresses.csv.gz`.

## Core Features
### 1. High Availability
* **Load Balancing:** Requests alternate between the two dataset containers to distribute query load.
* **Failover Logic:** If a gRPC call fails, the system sleeps for 100ms and retries the alternative node (up to 5 attempts total).

### 2. Specialized Caching
* **LRU Implementation:** Maintains an LRU cache of size 3.
* **Pre-fetching:** To optimize hit rates, the system fetches and stores 8 addresses per zipcode regardless of the initial request limit.
* **Independence:** The gateway can serve cached data even if the entire storage layer is offline.

## Implementation Details
* **gRPC Protocol:** Defined in `PropertyLookup.proto` using a `LookupByZip` RPC call.
* **Build Process:** Protocol Buffers are compiled during the Docker build stage to ensure environment consistency.

## Deployment

1. **Environment Setup**
   ```bash
   export PROJECT=p2
   
2. **Docker build**
   ```bash
   docker build -t $PROJECT-cache -f gateway/Dockerfile.cache .
   docker build -t $PROJECT-dataset -f storage/Dockerfile.dataset .
   docker compose up -d
