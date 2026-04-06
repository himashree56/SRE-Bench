import random
import datetime
import json
import uuid
from typing import Dict, List, Any, Optional

class SyntheticIncidentSimulator:
    """
    Generates high-fidelity synthetic microservices data (logs, metrics, alerts, deploys)
    for SREBench-Env scenarios.
    """
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.random = random.Random(seed)
        self.services = ["api-gateway", "auth-service", "payment-service", "db-proxy"]

    def generate_scenario(self, task_name: str) -> Dict[str, Any]:
        """Creates a deterministic, timestamp-perfect scenario."""
        # Reset local clock per scenario to ensure isolation
        self.start_time = datetime.datetime(2026, 4, 3, 10, 0, 0)
        # Use short UUID for readability in INC-{id}
        short_id = str(uuid.UUID(int=self.random.getrandbits(128)))[:8]
        self.incident_id = f"INC-{short_id}"
        
        if task_name == "alert-classifier":
            return self._create_easy_scenario()
        elif task_name == "root-cause-correlator":
            return self._create_medium_scenario()
        elif task_name == "incident-commander":
            return self._create_hard_scenario()
        else:
            raise ValueError(f"Unknown task: {task_name}")

    def _create_easy_scenario(self) -> Dict[str, Any]:
        """Task 1: Alert Classifier — Signal in logs/metrics for triage."""
        alerts = [
            {"id": "A1", "severity": "P1", "service": "auth-service", "title": "High Error Rate (>40%)", "triggered_at": self.start_time.isoformat(), "description": "Auth service is failing to validate tokens."},
            {"id": "A2", "severity": "P2", "service": "api-gateway", "title": "Monitor Flapping", "triggered_at": (self.start_time + datetime.timedelta(minutes=2)).isoformat(), "description": "Connectivity test is intermittent."},
            {"id": "A3", "severity": "P3", "service": "payment-service", "title": "Slight Latency Bump", "triggered_at": self.start_time.isoformat(), "description": "Slight p99 increase observed."}
        ]
        
        # Signal logs: actual errors for the P1 service
        auth_logs = [
            self._make_log("auth-service", "ERROR", "Invalid JWT: Signature verification failed", offset_sec=i*10) 
            for i in range(5)
        ]
        
        # Metrics: map ISO strings as keys
        error_metrics = {
            (self.start_time - datetime.timedelta(minutes=i)).isoformat(): 0.45 
            for i in range(5)
        }
        
        return {
            "incident_id": self.incident_id,
            "scenario": "alert-classifier",
            "ground_truth": {"root_cause_service": "auth-service", "root_cause_severity": "P1"},
            "services": self.services,
            "alerts": alerts,
            "logs": {"auth-service": auth_logs, "api-gateway": [], "payment-service": [], "db-proxy": []},
            "metrics": {"auth-service": {"error_rate": error_metrics}},
            "deployments": [],
            "runbooks": self.get_runbook_store()
        }

    def _create_medium_scenario(self) -> Dict[str, Any]:
        """Task 2: Root Cause Correlator — Chronological latency spike."""
        alerts = [
            {"id": "A1", "severity": "P2", "service": "payment-service", "title": "High Latency (p99 > 2000ms)", "triggered_at": self.start_time.isoformat(), "description": "Payment processing is timing out. High latency detected downstream of db-proxy."}
        ]
        
        # Chronological metrics: Low (normal) -> High (spike)
        latency_history = {}
        for i in range(15):
            ts = (self.start_time - datetime.timedelta(minutes=14-i)).isoformat()
            # If i < 3 (oldest), stable at 120ms. Then it jumps after the deploy (which is at t-12m)
            latency_history[ts] = 120 if i < 3 else (2100 + i*10)
        
        payment_logs = [
            self._make_log("payment-service", "ERROR", "Timeout waiting for database response", latency_ms=2150, offset_sec=i*12) 
            for i in range(5)
        ]
        
        # db-proxy slow query logs (real evidence)
        db_logs = [
            self._make_log("db-proxy", "WARN", "Slow query detected: SELECT * FROM tokens WHERE id = ?", latency_ms=1800, offset_sec=i*5)
            for i in range(3)
        ]
        
        deploys = [
            {"timestamp": (self.start_time - datetime.timedelta(minutes=12)).isoformat(), "service": "db-proxy", "version": "v1.2.4", "commit": "badc0de", "author": "dev-a"},
            {"timestamp": (self.start_time - datetime.timedelta(hours=2)).isoformat(), "service": "payment-service", "version": "v2.1.0", "commit": "a1b2c3d", "author": "dev-b"}
        ]
        
        return {
            "incident_id": self.incident_id,
            "scenario": "root-cause-correlator",
            "ground_truth": {"root_cause_service": "db-proxy", "correct_commit": "badc0de"},
            "services": self.services,
            "alerts": alerts,
            "logs": {"payment-service": payment_logs, "db-proxy": db_logs, "api-gateway": [], "auth-service": []},
            "metrics": {"payment-service": {"latency_p99": latency_history}},
            "deployments": deploys,
            "runbooks": self.get_runbook_store()
        }

    def _create_hard_scenario(self) -> Dict[str, Any]:
        """Task 3: Incident Commander — Red Herrings & Cascading errors."""
        alerts = [
            {"id": "A1", "severity": "P1", "service": "api-gateway", "title": "High Error Rate (>45%)", "triggered_at": self.start_time.isoformat(), "description": "Major breakage at edge."},
            {"id": "A2", "severity": "P2", "service": "auth-service", "title": "High Memory Usage (>90%)", "triggered_at": self.start_time.isoformat(), "description": "Memory saturation."},
            {"id": "A3", "severity": "P3", "service": "payment-service", "title": "Inbound Errors", "triggered_at": self.start_time.isoformat(), "description": "Failure cascading upstream."}
        ]
        
        # Red Herring Deploy: suspicious but NOT the cause
        deploys = [
            {"timestamp": (self.start_time + datetime.timedelta(minutes=1)).isoformat(), "service": "payment-service", "version": "v2.2.0", "commit": "badf00d", "author": "dev-x"},
            {"timestamp": (self.start_time - datetime.timedelta(days=1)).isoformat(), "service": "auth-service", "version": "v1.9.0", "commit": "fedcba9", "author": "dev-y"}
        ]
        
        auth_logs = [
            self._make_log("auth-service", "WARN", "Memory usage at 91%. GC overhead limit exceeded.", offset_sec=i*8) 
            for i in range(10)
        ]
        
        # Cascading error logs
        api_logs = [self._make_log("api-gateway", "ERROR", "Upstream auth-service returned 503", offset_sec=i*12) for i in range(5)]
        payment_logs = [self._make_log("payment-service", "ERROR", "Auth verification failed: service unavailable", offset_sec=i*15) for i in range(5)]
        
        # ISO Metrics with gradual climb for memory leak
        memory_progression = [0.70, 0.78, 0.85, 0.90, 0.92]
        memory_metrics = {
            (self.start_time - datetime.timedelta(minutes=4-i)).isoformat(): memory_progression[i]
            for i in range(5)
        }
        error_metrics = {
            (self.start_time - datetime.timedelta(minutes=i)).isoformat(): 0.45 
            for i in range(5)
        }
        
        return {
            "incident_id": self.incident_id,
            "scenario": "incident-commander",
            "ground_truth": {"root_cause_service": "auth-service", "root_cause_type": "memory_leak", "correct_action": "restart_service"},
            "services": self.services,
            "alerts": alerts,
            "logs": {"auth-service": auth_logs, "api-gateway": api_logs, "payment-service": payment_logs, "db-proxy": []},
            "metrics": {
                "auth-service": {"memory_usage": memory_metrics},
                "api-gateway": {"error_rate": error_metrics}
            },
            "deployments": deploys,
            "runbooks": self.get_runbook_store()
        }

    def _make_log(self, service: str, level: str, msg: str, latency_ms: int = 100, offset_sec: int = 0) -> str:
        """Helper to create a structured JSON log line with variable timestamp."""
        ts = (self.start_time + datetime.timedelta(seconds=offset_sec)).isoformat()
        log_data = {
            "timestamp": ts,
            "level": level,
            "service": service,
            "msg": msg,
            "latency_ms": latency_ms,
            "request_id": f"req-{self.random.randint(100000, 999999)}"
        }
        return json.dumps(log_data)

    def get_runbook_store(self) -> List[Dict[str, str]]:
        """Provides a searchable list of runbooks."""
        return [
            {
                "title": "Memory Leak Mitigation",
                "content": "If a service hits >90% heap usage, restart it immediately to clear the leak. Check GC logs for confirmation.",
                "tags": "memory, leak, saturation, auth-service, restart"
            },
            {
                "title": "Rollback Procedure",
                "content": "In case of latent degradation following a deployment, revert the service to the last known stable commit hash.",
                "tags": "deploy, rollback, rollback_deploy, revert"
            },
            {
                "title": "Database Connectivity Issues",
                "content": "High db-proxy latency often points to slow queries or connection pool exhaustion. Check db logs for slow queries.",
                "tags": "db, sql, query, latency, db-proxy"
            },
            {
                "title": "Auth Failures Triage",
                "content": "P1 auth failures often involve invalid signatures or token expiration. Verify JWT metadata in auth-service logs.",
                "tags": "auth, jwt, token, p1"
            }
        ]
