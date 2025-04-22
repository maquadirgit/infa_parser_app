import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import io

def extract_logic_from_transformation(transformation, transformation_type):
    records = []
    if transformation_type == "Expression":
        for instance in transformation.findall(".//TRANSFORMFIELD"):
            field = instance.get("NAME")
            logic = instance.get("EXPRESSION") or ""
            if logic.strip() and field != logic:
                records.append((transformation_type, transformation.get("NAME"), field, logic))

    elif transformation_type == "Lookup Procedure":
        override = transformation.find(".//TABLEATTRIBUTE[@NAME='Lookup Sql Override']")
        condition = transformation.find(".//TABLEATTRIBUTE[@NAME='Lookup condition']")
        sql_logic = override.get("VALUE").strip() if override is not None else ""
        cond_logic = condition.get("VALUE").strip() if condition is not None else ""
        if sql_logic:
            records.append((transformation_type, transformation.get("NAME"), "Lookup SQL Override", sql_logic))
        if cond_logic:
            records.append((transformation_type, transformation.get("NAME"), "Lookup Condition", cond_logic))

    elif transformation_type == "Source Qualifier":
        sql_override = transformation.find(".//TABLEATTRIBUTE[@NAME='Sql Query']")
        if sql_override is not None:
            sql = sql_override.get("VALUE")
            if sql and sql.strip():
                records.append((transformation_type, transformation.get("NAME"), "Source Qualifier SQL", sql.strip()))

    elif transformation_type == "Router":
        for group in transformation.findall(".//GROUP"):
            group_name = group.get("NAME")
            cond = group.get("CONDITION") or ""
            if cond.strip():
                records.append((transformation_type, transformation.get("NAME"), f"Group: {group_name}", cond.strip()))

    elif transformation_type == "Joiner":
        for attr in transformation.findall(".//TABLEATTRIBUTE"):
            if attr.get("NAME") in ("Join Condition", "Source Filter"):
                val = attr.get("VALUE") or ""
                if val.strip():
                    records.append((transformation_type, transformation.get("NAME"), attr.get("NAME"), val.strip()))

    elif transformation_type == "Update Strategy":
        for attr in transformation.findall(".//TABLEATTRIBUTE"):
            if attr.get("NAME") == "Update Strategy Expression":
                logic = attr.get("VALUE") or ""
                if logic.strip():
                    records.append((transformation_type, transformation.get("NAME"), "Update Strategy", logic.strip()))

    elif transformation_type == "SQL":
        for attr in transformation.findall(".//TABLEATTRIBUTE"):
            if attr.get("NAME") in ("Sql Query", "User Defined Join"):
                val = attr.get("VALUE") or ""
                if val.strip():
                    records.append((transformation_type, transformation.get("NAME"), attr.get("NAME"), val.strip()))

    elif transformation_type == "Target":
        for attr in transformation.findall(".//TABLEATTRIBUTE"):
            if "sql" in attr.get("NAME", "").lower():
                val = attr.get("VALUE") or ""
                if val.strip():
                    records.append((transformation_type, transformation.get("NAME"), attr.get("NAME"), val.strip()))

    return records

def parse_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    transformation_types = [
        "Expression", "Lookup Procedure", "Joiner", "Router", "Source Qualifier",
        "Update Strategy", "SQL", "Target"
    ]
    all_records = []

    for trans_type in transformation_types:
        for transformation in root.findall(f".//TRANSFORMATION[@TYPE='{trans_type}']"):
            extracted = extract_logic_from_transformation(transformation, trans_type)
            all_records.extend(extracted)

    return all_records

# ------------------ Streamlit UI ------------------

st.set_page_config(page_title="Informatica XML Parser", layout="centered")
st.title("Informatica Mapping Logic Extractor")

uploaded_file = st.file_uploader("Upload Informatica XML File", type="xml")

if uploaded_file:
    try:
        records = parse_xml(uploaded_file)
        if not records:
            st.warning("No logic records found in the uploaded XML.")
        else:
            df = pd.DataFrame(records, columns=["Transformation Type", "Transformation Name", "Field", "Logic"])
            df = df[df["Field"] != df["Logic"]]  # filter Field == Logic
            df = df[df["Logic"].notna() & df["Logic"].str.strip().astype(bool)]  # non-empty logic

            st.success("Logic extraction successful!")
            st.dataframe(df)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name="Transformation Logic")
            st.download_button(
                label="Download Excel",
                data=output.getvalue(),
                file_name="infa_transformation_logic.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Error processing XML: {e}")
