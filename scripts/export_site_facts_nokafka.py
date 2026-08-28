"""Wrapper to export site facts without Kafka deps by stubbing confluent_kafka."""
import sys
import types

# Minimal stub so module import succeeds without installing confluent_kafka.
sys.modules.setdefault("confluent_kafka", types.SimpleNamespace(Producer=object))
# FastAvro is only used by BaseKafkaProducer; stubbing suffices for import-time.
sys.modules.setdefault("fastavro", types.SimpleNamespace())

from export_site_facts import main

if __name__ == "__main__":
    main()

