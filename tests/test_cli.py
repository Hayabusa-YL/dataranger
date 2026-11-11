from dataranger import __version__
from dataranger.cli import main


def test_version_string():
    assert __version__.count(".") == 2


def test_plan_lists_six_stages(capsys):
    assert main(["plan"]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 6 and out[3].startswith("4. Verify")


def test_patrol_reads_schema_qualified_tables(tmp_path):
    import duckdb
    from datetime import date, timedelta

    from dataranger.bench import generate, inject

    case = inject(generate(7, "small", start=date.today() - timedelta(days=60)))
    db = str(tmp_path / "shop.duckdb")
    con = duckdb.connect(db)
    con.execute("create schema gold")
    for name, df in [("transactions", case.warehouse["transactions"]),
                     ("customers", case.warehouse["customers"]),
                     ("manifest", case.manifest)]:
        con.register(f"src_{name}", df)
        con.execute(f"create table gold.{name} as select * from src_{name}")
    con.close()

    out = tmp_path / "report"
    rc = main(["patrol", "--db", db, "--table", "gold.transactions", "--ref-table", "gold.customers",
               "--manifest-table", "gold.manifest", "--out", str(out)])
    assert rc == 0
    assert (out / "dashboard.html").exists()

    con = duckdb.connect(db)
    con.execute("create table transactions as select * from gold.transactions")
    con.execute("create table customers as select * from gold.customers")
    con.execute("create table manifest as select * from gold.manifest")
    con.close()

    from dataranger.patrol import from_duckdb
    facts, refs, man = from_duckdb(db, "transactions", "customers", "manifest")
    assert len(facts) == len(case.warehouse["transactions"])
