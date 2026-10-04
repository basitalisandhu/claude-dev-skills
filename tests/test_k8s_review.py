from conftest import load_script, run_json, run_main

mod = load_script("devops", "k8s-manifest-review", "k8s_review.py")

BAD = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 1
  template:
    spec:
      hostNetwork: true
      volumes:
      - name: sock
        hostPath:
          path: /var/run/docker.sock
      containers:
      - name: web
        image: nginx
        env:
        - name: DB_PASSWORD
          value: supersecretvalue
        securityContext:
          privileged: true
          capabilities:
            add: [SYS_ADMIN]
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: prod
spec:
  type: LoadBalancer
---
apiVersion: v1
kind: Secret
metadata:
  name: creds
  namespace: prod
stringData:
  password: hunter2
"""

GOOD = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: prod
spec:
  replicas: 2
  template:
    spec:
      serviceAccountName: web
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: web
        image: nginx:1.27.1
        resources:
          requests: {cpu: 100m, memory: 64Mi}
          limits: {memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: [ALL]
        livenessProbe:
          httpGet: {path: /healthz, port: 8080}
        readinessProbe:
          httpGet: {path: /ready, port: 8080}
"""


def test_bad_manifests(write, tmp_path):
    f = write("bad.yaml", BAD)
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 1 and rep["objects"] == 3
    ids = {x["id"] for x in rep["findings"]}
    for expected in ["K8S-001", "K8S-002", "K8S-003", "K8S-004", "K8S-005", "K8S-006", "K8S-007", "K8S-008", "K8S-009", "K8S-010", "K8S-011", "K8S-012", "K8S-013", "K8S-014", "K8S-015", "K8S-016"]:
        assert expected in ids, expected
    hostpath = [x for x in rep["findings"] if x["id"] == "K8S-008" and "hostPath" in x["where"]][0]
    assert hostpath["severity"] == "critical"
    assert rep["counts"]["critical"] == 2


def test_good_manifest_is_clean(write, tmp_path):
    f = write("good.yaml", GOOD)
    rc, rep = run_json(mod, [str(f), "--json", "--fail-on", "info"])
    assert rc == 0, rep["findings"]


def test_cronjob_pod_spec_and_list_kind(write, tmp_path):
    cj = """apiVersion: batch/v1
kind: CronJob
metadata: {name: nightly, namespace: ops}
spec:
  schedule: "0 4 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: job
            image: busybox:1.36
"""
    f = write("cj.yaml", cj)
    rc, rep = run_json(mod, [str(f), "--json"])
    ids = {x["id"] for x in rep["findings"]}
    assert "K8S-001" in ids and "K8S-009" not in ids  # no probes expected for a job
    lst = '{"kind": "List", "items": [{"kind": "Pod", "metadata": {"name": "p"}, "spec": {"containers": [{"name": "c", "image": "a:latest"}]}}]}'
    f2 = write("list.json", lst)
    rc, rep = run_json(mod, [str(f2), "--json"])
    assert rep["objects"] == 1 and "K8S-007" in {x["id"] for x in rep["findings"]}


def test_errors(write, tmp_path):
    write("d/bad.yml", "a:\n\tb\n")
    rc, rep = run_json(mod, [str(tmp_path / "d"), "--json"])
    assert rc == 2 and rep["parse_errors"]
    rc, _, _ = run_main(mod, [str(tmp_path / "nope")])
    assert rc == 2
    f = write("empty.yaml", "")
    rc, out, _ = run_main(mod, [str(f)])
    assert rc == 0 and "0 objects" in out
