from conftest import load_script, run_json, run_main

mod = load_script("data", "csv-profiler", "csv_profiler.py")

CSV = """id,name,amount,active,joined,note
1,Ann,10.50,true,2024-01-02,
2,Bob,-3,false,2024-02-03,hello
3,Cy ,NULL,true,2024-03-04,
4,Dee,7,true,not a date,x
4,Dee,7,true,not a date,x
5,Eve,"1,000",yes,2024-05-06,
6,Fay,2,true,2024-06-07,note,extra
"""


def test_profile_types_and_stats(write, tmp_path):
    f = write("d.csv", CSV)
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 0
    assert rep["delimiter"] == "," and rep["rows"] == 7 and rep["columns_count"] == 6
    cols = {c["name"]: c for c in rep["columns"]}
    assert cols["id"]["type"] == "integer" and cols["id"]["min"] == 1 and cols["id"]["max"] == 6 and cols["id"]["unique"] is False
    assert cols["amount"]["type"] == "number" and cols["amount"]["nulls"] == 1 and cols["amount"]["negatives"] == 1 and cols["amount"]["max"] == 1000.0
    assert cols["active"]["type"] == "boolean"
    assert cols["joined"]["type"] == "string" and "date" in cols["joined"]["mixed_types"]
    assert cols["name"]["leading_or_trailing_space"] == 1
    assert rep["candidate_keys"] == []
    assert rep["duplicate_rows"] == 1
    assert rep["ragged_rows"] == [8]
    assert any("duplicate rows" in w for w in rep["warnings"]) and any("mixes types" in w for w in rep["warnings"])


def test_tsv_no_header_and_sample(write, tmp_path):
    f = write("d.tsv", "a\t1\nb\t2\nc\t3\n")
    rc, rep = run_json(mod, [str(f), "--json", "--no-header", "--delimiter", "tab", "--sample", "2"])
    assert rep["delimiter"] == "\t" and rep["rows"] == 2
    assert [c["name"] for c in rep["columns"]] == ["col1", "col2"]
    assert rep["columns"][1]["type"] == "integer"


def test_strict_and_text(write, tmp_path):
    f = write("c.csv", "a,b\n1,x\n1,y\n")
    rc, out, _ = run_main(mod, [str(f)])
    assert rc == 0 and "constant" in out and "candidate keys" in out
    rc, _, _ = run_main(mod, [str(f), "--strict"])
    assert rc == 1


def test_errors(write, tmp_path):
    f = write("e.csv", "\n\n")
    rc, _, err = run_main(mod, [str(f)])
    assert rc == 2 and "empty" in err
    rc, _, _ = run_main(mod, [str(tmp_path / "nope.csv")])
    assert rc == 2


def test_classify():
    c = mod.classify
    assert c("12") == "integer" and c("1,234") == "integer" and c("3.5") == "number" and c("1e5") == "number"
    assert c("2024-01-01") == "date" and c("2024-01-01T10:00:00Z") == "datetime" and c("yes") == "boolean"
    assert c("N/A") == "null" and c("hello") == "string"


def test_crlf_with_bom(write, tmp_path):
    content = "\ufeffid,name\r\n1,Ann\r\n2,Bob\r\n"
    f = write("crlf_bom.csv", content)
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 0
    assert rep["dialect"]["bom"] is True
    assert rep["dialect"]["line_terminator"] == "CRLF"
    assert [c["name"] for c in rep["columns"]] == ["id", "name"]
    assert any("BOM" in w for w in rep["warnings"])


def test_single_quoted(write, tmp_path):
    content = "id,name\n1,'Ann, A'\n2,'Bob'\n"
    f = write("squote.csv", content)
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 0
    assert rep["dialect"]["quotechar"] == "'"


def test_doublequote_reported_only_when_escaped(write, tmp_path):
    f1 = write("plain_quote.csv", 'id,name\n1,"Ann"\n2,"Bob"\n')
    rc, rep1 = run_json(mod, [str(f1), "--json"])
    assert rc == 0
    assert "doublequote" not in rep1["dialect"]

    f2 = write("escaped.csv", 'id,name\n1,"Ann ""A"" Smith"\n')
    rc, rep2 = run_json(mod, [str(f2), "--json"])
    assert rc == 0
    assert rep2["dialect"]["doublequote"] is True

    f3 = write("empty_field.csv", 'id,name,note\n1,"",x\n')
    rc, rep3 = run_json(mod, [str(f3), "--json"])
    assert rc == 0
    assert "doublequote" not in rep3["dialect"]


def test_text_dialect_line(write, tmp_path):
    f = write("plain.csv", "a,b\n1,2\n")
    rc, out, _ = run_main(mod, [str(f)])
    assert rc == 0
    assert "dialect:" in out
    assert "line_terminator=LF" in out
    assert "bom=False" in out


def test_mixed_line_endings(write, tmp_path):
    content = "a,b\r\n1,2\n3,4\r\n"
    f = write("mixed.csv", content)
    rc, rep = run_json(mod, [str(f), "--json"])
    assert rc == 0
    assert rep["dialect"]["line_terminator"] == "mixed"
    assert any("mixed line endings" in w for w in rep["warnings"])
