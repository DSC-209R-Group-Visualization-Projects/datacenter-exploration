"""Clean datacenterbans.com policy tables (state summaries, state bills, local actions).

Inputs:  data/raw/datacenterbans/{states,state_bills,local_actions}.csv (from parse_datacenterbans.py)
Outputs: data/clean/policy_states.csv, policy_state_bills.csv, policy_local_actions.csv,
         data/clean/policy_county_summary.csv   one row per county with any local action
"""
import re

import numpy as np
import pandas as pd

from common import CLEAN, RAW

SRC = RAW / "datacenterbans"
RESTRICTIVE = {"moratorium", "ban", "construction_pause", "permit_freeze"}  # zoning_restriction regulates rather than stops


def bill_outcome(s):
    t = str(s).lower()
    if re.search(r"veto", t) and not re.search(r"signed", t):
        return "vetoed"
    if re.search(r"died|dead|failed|stalled|did not pass|not pass|sine die|withdrawn|session ended", t):
        return "died"
    if re.search(r"signed|enacted|announced|approved|law\b", t):
        return "enacted"
    if re.search(r"committee|introduc|carried over|advanced|referred|pending|hearing|passed", t):
        return "pending"
    return "other"


def main():
    ref = pd.read_csv(CLEAN / "counties.csv", dtype={"geoid": str}, usecols=["geoid", "state", "county_name"])

    s = pd.read_csv(SRC / "states.csv", dtype={"state_fips": str})
    s["last_updated"] = pd.to_datetime(s["last_updated"])
    s["has_local_restrictions"] = s["tags"].fillna("").str.contains("local_restrictions")
    s["has_favorable_tag"] = s["tags"].fillna("").str.contains("favorable")
    s.to_csv(CLEAN / "policy_states.csv", index=False)

    b = pd.read_csv(SRC / "state_bills.csv")
    b["outcome"] = b["status"].map(bill_outcome)
    b["status_date"] = pd.to_datetime(b["status"].str.extract(r"((?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4})")[0],
                                      format="%B %d, %Y", errors="coerce")
    b = b.rename(columns={"status": "status_raw", "id": "bill_id"})
    b.to_csv(CLEAN / "policy_state_bills.csv", index=False)

    l = pd.read_csv(SRC / "local_actions.csv", dtype={"countyFips": str})
    l = l.rename(columns={"countyFips": "county_geoid", "type": "action_type", "status": "action_status"})
    l["county_geoid"] = l["county_geoid"].str.zfill(5)
    l["date"] = pd.to_datetime(l["date"], errors="coerce")
    l["geoid_valid"] = l["county_geoid"].isin(ref["geoid"])
    l["geoid_state_match"] = l["county_geoid"].map(ref.set_index("geoid")["state"]).eq(l["state"])
    l["is_restrictive"] = l["action_type"].isin(RESTRICTIVE)
    # "enacted" and "active" are both in force; "proposed" is not yet; "rejected"/"expired" are not.
    l["in_force"] = l["action_status"].isin(["active", "enacted"])
    l["ballot_related"] = l["description"].fillna("").str.contains(r"\bballot|referendum|voters? (?:approved|rejected)|special election", case=False)
    l["is_city"] = l["locality"].str.contains(r"^(?:City|Town|Village|Borough) of", case=False)
    l = l.drop_duplicates(["state", "locality", "action_type", "date", "county_geoid"])
    l.to_csv(CLEAN / "policy_local_actions.csv", index=False)

    c = l.groupby("county_geoid").agg(
        n_actions=("locality", "size"), n_localities=("locality", "nunique"),
        n_restrictive_in_force=("is_restrictive", lambda x: int((x & l.loc[x.index, "in_force"]).sum())),
        n_proposed=("action_status", lambda x: int((x == "proposed").sum())),
        n_rejected=("action_status", lambda x: int((x == "rejected").sum())),
        first_action=("date", "min"), last_action=("date", "max")).reset_index()
    c["any_restriction_in_force"] = c["n_restrictive_in_force"] > 0
    c.to_csv(CLEAN / "policy_county_summary.csv", index=False)

    print(f"states {len(s)}; bills {len(b)} outcomes {b.outcome.value_counts().to_dict()}")
    print(f"local actions {len(l)} (invalid geoid {int((~l.geoid_valid).sum())}, state mismatch {int((~l.geoid_state_match).sum())}); "
          f"in force {int(l.in_force.sum())}; restrictive in force {int((l.in_force & l.is_restrictive).sum())}; ballot-related {int(l.ballot_related.sum())}")
    print(f"counties with action {len(c)}; with restriction in force {int(c.any_restriction_in_force.sum())}")
    print(l.loc[~l.geoid_state_match, ["state", "locality", "county_geoid"]].head(8).to_string(index=False))
    print(b[b.outcome == "other"][["state", "bill_id", "status_raw"]].head(8).to_string(index=False))


if __name__ == "__main__":
    main()
