#!/usr/bin/env python3
"""Author Retail Tableau workbooks (.twb) and package as .twbx.

Produces:
  tableau/workbooks/Retail_Ops_Dashboard_v3.twbx  (primary: Sales + Service pages)
  tableau/workbooks/Retail_Sales_Dashboard_v3.twbx  (opens on Overview)
  tableau/workbooks/Retail_Service_Dashboard_v3.twbx  (opens on Overview)
  tableau/workbooks/Retail_Sales_Report.twbx
  tableau/workbooks/Retail_Service_Satisfaction_Report.twbx

Textscan CSV connections are embedded so Desktop / Public can open without
a separate data hunt. Hyper extracts are included when present.
Openability: braced simple-id UUIDs; dashboard Desktop device layouts;
worksheet tabs stay visible (no blanket hidden=true). No INDEX() Top-N store filter.
"""

from __future__ import annotations

import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "tableau" / "marts"
EXTRACTS = ROOT / "tableau" / "Data" / "Extracts"
OUT = ROOT / "tableau" / "workbooks"


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def new_uuid() -> str:
    """Tableau requires braced UUIDs: {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}."""
    return "{" + str(uuid.uuid4()) + "}"


def simple_id_xml(indent: str = "      ") -> str:
    return f'{indent}<simple-id uuid="{new_uuid()}" />'


def _brace_uuid(value: str | None) -> str:
    if not value:
        return new_uuid()
    v = value.strip()
    if v.startswith("{") and v.endswith("}"):
        return v
    return "{" + v + "}"


def ensure_content_models(root: ET.Element) -> None:
    """Guarantee Tableau content-model required children (worksheet / dashboard / window).

    Worksheets: trailing <simple-id> after <table>.
    Dashboards: <datasources>, <devicelayouts> with >=1 <devicelayout>, <simple-id>
    after zones. Empty <devicelayouts/> is invalid.
    Windows: trailing <simple-id>.
    All simple-id uuid values must be braced.
    """
    ds_names: list[str] = []
    for ds in root.findall("./datasources/datasource"):
        name = ds.get("name")
        if name and name not in ds_names:
            ds_names.append(name)
    if "Parameters" not in ds_names:
        ds_names.append("Parameters")

    def _ensure_simple_id(el: ET.Element) -> None:
        sid = el.find("simple-id")
        if sid is None:
            ET.SubElement(el, "simple-id", {"uuid": new_uuid()})
        else:
            sid.set("uuid", _brace_uuid(sid.get("uuid")))

    for ws in root.findall("./worksheets/worksheet"):
        _ensure_simple_id(ws)

    for dash in root.findall("./dashboards/dashboard"):
        children = list(dash)
        tags = [c.tag for c in children]

        if "datasources" not in tags:
            ds_el = ET.Element("datasources")
            for name in ds_names:
                ET.SubElement(ds_el, "datasource", {"name": name})
            if "zones" in tags:
                dash.insert(tags.index("zones"), ds_el)
            else:
                dash.append(ds_el)
            children = list(dash)
            tags = [c.tag for c in children]

        dl_el = dash.find("devicelayouts")
        if dl_el is None:
            dl_el = ET.Element("devicelayouts")
            if "zones" in tags:
                dash.insert(tags.index("zones") + 1, dl_el)
            else:
                dash.append(dl_el)
            children = list(dash)
            tags = [c.tag for c in children]
        # Empty <devicelayouts/> is invalid — require a Desktop layout child
        if dl_el.find("devicelayout") is None:
            size_el = dash.find("size")
            attrs = {
                "maxheight": size_el.get("maxheight", "900") if size_el is not None else "900",
                "maxwidth": size_el.get("maxwidth", "1400") if size_el is not None else "1400",
                "minheight": size_el.get("minheight", "900") if size_el is not None else "900",
                "minwidth": size_el.get("minwidth", "1400") if size_el is not None else "1400",
                "sizing-mode": size_el.get("sizing-mode", "fixed") if size_el is not None else "fixed",
            }
            layout = ET.SubElement(dl_el, "devicelayout", {"name": "Desktop"})
            ET.SubElement(layout, "size", attrs)

        _ensure_simple_id(dash)

    for win in root.findall("./windows/window"):
        _ensure_simple_id(win)




def kpi_sheet(ds: str, caption: str, name: str, title: str, measure: str, derivation: str, instance: str, dtype: str = "real") -> str:
    return f"""
    <worksheet name='{esc(name)}'>
      <layout-options>
        <title>
          <formatted-text>
            <run fontcolor='#5B6B7C' fontname='Arial' fontsize='10' bold='true'>{esc(title)}</run>
          </formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{esc(caption)}' name='{ds}' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
            <column datatype='{dtype}' name='[{measure}]' role='measure' type='quantitative' />
            <column-instance column='[{measure}]' derivation='{derivation}' name='[{instance}]' pivot='key' type='quantitative' />
          </datasource-dependencies>
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Text' />
            <encodings>
              <text column='[{ds}].[{instance}]' />
            </encodings>
          </pane>
        </panes>
        <rows /><cols />
      </table>
    </worksheet>
"""


def calc_kpi_sheet(ds: str, caption: str, name: str, title: str, calc_name: str) -> str:
    return f"""
    <worksheet name='{esc(name)}'>
      <layout-options>
        <title>
          <formatted-text>
            <run fontcolor='#5B6B7C' fontname='Arial' fontsize='10' bold='true'>{esc(title)}</run>
          </formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{esc(caption)}' name='{ds}' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
            <column datatype='real' name='[{calc_name}]' role='measure' type='quantitative' />
            <column-instance column='[{calc_name}]' derivation='User' name='[usr:{calc_name}:qk]' pivot='key' type='quantitative' />
          </datasource-dependencies>
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Text' />
            <encodings>
              <text column='[{ds}].[usr:{calc_name}:qk]' />
            </encodings>
          </pane>
        </panes>
        <rows /><cols />
      </table>
    </worksheet>
"""


def bar_sheet(
    ds: str,
    caption: str,
    name: str,
    title: str,
    dim: str,
    measure: str,
    measure_derivation: str,
    measure_instance: str,
    horizontal: bool = True,
    color_dim: str | None = None,
    measure_dtype: str = "real",
) -> str:
    dim_inst = f"none:{dim}:nk"
    rows = f"[{ds}].[{dim_inst}]" if horizontal else f"[{ds}].[{measure_instance}]"
    cols = f"[{ds}].[{measure_instance}]" if horizontal else f"[{ds}].[{dim_inst}]"
    color_xml = ""
    color_dep = ""
    if color_dim:
        color_dep = f"""
            <column datatype='string' name='[{color_dim}]' role='dimension' type='nominal' />
            <column-instance column='[{color_dim}]' derivation='None' name='[none:{color_dim}:nk]' pivot='key' type='nominal' />"""
        color_xml = f"""
              <color column='[{ds}].[none:{color_dim}:nk]' />"""
    return f"""
    <worksheet name='{esc(name)}'>
      <layout-options>
        <title>
          <formatted-text>
            <run fontcolor='#1F2A37' fontname='Arial' fontsize='12' bold='true'>{esc(title)}</run>
          </formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{esc(caption)}' name='{ds}' />
            <datasource name='Parameters' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
            <column datatype='string' name='[{dim}]' role='dimension' type='nominal' />
            <column datatype='{measure_dtype}' name='[{measure}]' role='measure' type='quantitative' />
            <column-instance column='[{dim}]' derivation='None' name='[{dim_inst}]' pivot='key' type='nominal' />
            <column-instance column='[{measure}]' derivation='{measure_derivation}' name='[{measure_instance}]' pivot='key' type='quantitative' />{color_dep}
          </datasource-dependencies>
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Bar' />
            <encodings>{color_xml}
            </encodings>
          </pane>
        </panes>
        <rows>{rows}</rows>
        <cols>{cols}</cols>
      </table>
    </worksheet>
"""


def line_sheet(ds: str, caption: str, name: str, title: str, date_dim: str, measure: str, m_deriv: str, m_inst: str, measure_dtype: str = "real") -> str:
    return f"""
    <worksheet name='{esc(name)}'>
      <layout-options>
        <title>
          <formatted-text>
            <run fontcolor='#1F2A37' fontname='Arial' fontsize='12' bold='true'>{esc(title)}</run>
          </formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{esc(caption)}' name='{ds}' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
            <column datatype='date' name='[{date_dim}]' role='dimension' type='ordinal' />
            <column datatype='{measure_dtype}' name='[{measure}]' role='measure' type='quantitative' />
            <column-instance column='[{date_dim}]' derivation='None' name='[none:{date_dim}:ok]' pivot='key' type='ordinal' />
            <column-instance column='[{measure}]' derivation='{m_deriv}' name='[{m_inst}]' pivot='key' type='quantitative' />
          </datasource-dependencies>
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Line' />
          </pane>
        </panes>
        <rows>[{ds}].[{m_inst}]</rows>
        <cols>[{ds}].[none:{date_dim}:ok]</cols>
      </table>
    </worksheet>
"""


def heatmap_sheet(ds: str, caption: str, name: str, title: str, row_dim: str, col_dim: str, measure: str, m_deriv: str, m_inst: str, measure_dtype: str = "integer") -> str:
    return f"""
    <worksheet name='{esc(name)}'>
      <layout-options>
        <title>
          <formatted-text>
            <run fontcolor='#1F2A37' fontname='Arial' fontsize='12' bold='true'>{esc(title)}</run>
          </formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{esc(caption)}' name='{ds}' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
            <column datatype='string' name='[{row_dim}]' role='dimension' type='nominal' />
            <column datatype='string' name='[{col_dim}]' role='dimension' type='nominal' />
            <column datatype='{measure_dtype}' name='[{measure}]' role='measure' type='quantitative' />
            <column-instance column='[{row_dim}]' derivation='None' name='[none:{row_dim}:nk]' pivot='key' type='nominal' />
            <column-instance column='[{col_dim}]' derivation='None' name='[none:{col_dim}:nk]' pivot='key' type='nominal' />
            <column-instance column='[{measure}]' derivation='{m_deriv}' name='[{m_inst}]' pivot='key' type='quantitative' />
          </datasource-dependencies>
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Square' />
            <encodings>
              <color column='[{ds}].[{m_inst}]' />
            </encodings>
          </pane>
        </panes>
        <rows>[{ds}].[none:{row_dim}:nk]</rows>
        <cols>[{ds}].[none:{col_dim}:nk]</cols>
      </table>
    </worksheet>
"""


def sheet_windows_xml(names: list[str], *, hidden: bool = False) -> str:
    """Emit worksheet <window> entries. When hidden=True, hide sheet tabs in Desktop."""
    out = ""
    hidden_attr = " hidden='true'" if hidden else ""
    for sn in names:
        out += f"""
    <window class='worksheet' maximized='false'{hidden_attr} name='{esc(sn)}'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'><card type='columns' /></strip>
          <strip size='2147483647'><card type='rows' /></strip>
          <strip size='30'><card type='title' /></strip>
        </edge>
      </cards>
    </window>
"""
    return out


def textscan_ds(
    ds_name: str,
    caption: str,
    nc_name: str,
    filename: str,
    columns_xml: str,
    field_mappings: str,
    calcs: str,
) -> str:
    return f"""
    <datasource caption='{esc(caption)}' inline='true' name='{ds_name}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='{esc(filename)}' name='{nc_name}'>
            <connection class='textscan' directory='Data/Datasources' filename='{esc(filename)}' password='' server='' />
          </named-connection>
        </named-connections>
        <relation connection='{nc_name}' name='{esc(filename)}' table='[{filename.replace(".csv", "#csv")}]' type='table'>
          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>
{columns_xml}
          </columns>
        </relation>
        <metadata-records>
          <metadata-record class='capability'>
            <remote-name />
            <remote-type>0</remote-type>
            <parent-name>[{esc(filename)}]</parent-name>
            <remote-alias />
            <aggregation>Count</aggregation>
            <contains-null>true</contains-null>
          </metadata-record>
        </metadata-records>
      </connection>
      <aliases enabled='yes' />
{calcs}
{field_mappings}
      <layout dim-ordering='alphabetic' dim-percentage='0.5' measure-ordering='alphabetic' measure-percentage='0.5' show-structure='true' />
    </datasource>
"""


def create_sales_twb() -> str:
    ds = "federated.daily_sales_store"
    ds_cat = "federated.daily_sales_category"
    ds_ch = "federated.channel_mix"
    ds_prod = "federated.product_perf"
    cap = "Daily Sales by Store"
    cap_cat = "Daily Sales by Category"
    cap_ch = "Channel Mix"
    cap_prod = "Product Performance"

    store_cols = """
            <column datatype='date' name='transaction_date' ordinal='0' />
            <column datatype='string' name='store_id' ordinal='1' />
            <column datatype='string' name='store_name' ordinal='2' />
            <column datatype='string' name='region' ordinal='3' />
            <column datatype='string' name='store_type' ordinal='4' />
            <column datatype='integer' name='transactions' ordinal='5' />
            <column datatype='integer' name='units_sold' ordinal='6' />
            <column datatype='real' name='gross_revenue' ordinal='7' />
            <column datatype='real' name='net_revenue' ordinal='8' />
            <column datatype='real' name='discount_total' ordinal='9' />
            <column datatype='real' name='cogs' ordinal='10' />
            <column datatype='real' name='gross_profit' ordinal='11' />
            <column datatype='real' name='avg_order_value' ordinal='12' />
            <column datatype='real' name='gross_margin_pct' ordinal='13' />
"""
    store_fields = """
      <column caption='Transaction Date' datatype='date' name='[transaction_date]' role='dimension' type='ordinal' />
      <column caption='Store Id' datatype='string' name='[store_id]' role='dimension' type='nominal' />
      <column caption='Store Name' datatype='string' name='[store_name]' role='dimension' type='nominal' />
      <column caption='Region' datatype='string' name='[region]' role='dimension' type='nominal' />
      <column caption='Store Type' datatype='string' name='[store_type]' role='dimension' type='nominal' />
      <column caption='Transactions' datatype='integer' name='[transactions]' role='measure' type='quantitative' />
      <column caption='Units Sold' datatype='integer' name='[units_sold]' role='measure' type='quantitative' />
      <column caption='Gross Revenue' datatype='real' name='[gross_revenue]' role='measure' type='quantitative' />
      <column caption='Net Revenue' datatype='real' name='[net_revenue]' role='measure' type='quantitative' />
      <column caption='Discount Total' datatype='real' name='[discount_total]' role='measure' type='quantitative' />
      <column caption='Cogs' datatype='real' name='[cogs]' role='measure' type='quantitative' />
      <column caption='Gross Profit' datatype='real' name='[gross_profit]' role='measure' type='quantitative' />
      <column caption='Avg Order Value' datatype='real' name='[avg_order_value]' role='measure' type='quantitative' />
      <column caption='Gross Margin Pct' datatype='real' name='[gross_margin_pct]' role='measure' type='quantitative' />
"""
    store_calcs = """
      <column caption='Net Revenue Total' datatype='real' default-format='cCurrency' name='[Calculation_Net_Revenue]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM([net_revenue])' />
      </column>
      <column caption='Order Count' datatype='integer' default-format='n#,##0' name='[Calculation_Orders]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM([transactions])' />
      </column>
      <column caption='AOV' datatype='real' default-format='cCurrency' name='[Calculation_AOV]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM([net_revenue]) / NULLIF(SUM([transactions]), 0)' />
      </column>
      <column caption='Gross Margin %' datatype='real' default-format='p0.0%' name='[Calculation_Gross_Margin_Pct]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM([gross_profit]) / NULLIF(SUM([net_revenue]), 0)' />
      </column>
      <column caption='Store Share of Total' datatype='real' default-format='p0.0%' name='[Calculation_Store_Share]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM([net_revenue]) / { FIXED : SUM([net_revenue]) }' />
      </column>
      <column caption='Region Avg Daily Revenue' datatype='real' default-format='cCurrency' name='[Calculation_Region_Avg_Daily]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='{ FIXED [region] : AVG([net_revenue]) }' />
      </column>
"""

    cat_cols = """
            <column datatype='date' name='transaction_date' ordinal='0' />
            <column datatype='string' name='category' ordinal='1' />
            <column datatype='integer' name='transactions' ordinal='2' />
            <column datatype='integer' name='units_sold' ordinal='3' />
            <column datatype='real' name='net_revenue' ordinal='4' />
            <column datatype='real' name='gross_profit' ordinal='5' />
"""
    cat_fields = """
      <column caption='Transaction Date' datatype='date' name='[transaction_date]' role='dimension' type='ordinal' />
      <column caption='Category' datatype='string' name='[category]' role='dimension' type='nominal' />
      <column caption='Transactions' datatype='integer' name='[transactions]' role='measure' type='quantitative' />
      <column caption='Units Sold' datatype='integer' name='[units_sold]' role='measure' type='quantitative' />
      <column caption='Net Revenue' datatype='real' name='[net_revenue]' role='measure' type='quantitative' />
      <column caption='Gross Profit' datatype='real' name='[gross_profit]' role='measure' type='quantitative' />
"""
    ch_cols = """
            <column datatype='date' name='transaction_date' ordinal='0' />
            <column datatype='string' name='channel' ordinal='1' />
            <column datatype='string' name='payment_method' ordinal='2' />
            <column datatype='integer' name='transactions' ordinal='3' />
            <column datatype='real' name='net_revenue' ordinal='4' />
"""
    ch_fields = """
      <column caption='Transaction Date' datatype='date' name='[transaction_date]' role='dimension' type='ordinal' />
      <column caption='Channel' datatype='string' name='[channel]' role='dimension' type='nominal' />
      <column caption='Payment Method' datatype='string' name='[payment_method]' role='dimension' type='nominal' />
      <column caption='Transactions' datatype='integer' name='[transactions]' role='measure' type='quantitative' />
      <column caption='Net Revenue' datatype='real' name='[net_revenue]' role='measure' type='quantitative' />
"""
    prod_cols = """
            <column datatype='string' name='product_id' ordinal='0' />
            <column datatype='string' name='category' ordinal='1' />
            <column datatype='string' name='brand' ordinal='2' />
            <column datatype='integer' name='units_sold' ordinal='3' />
            <column datatype='real' name='net_revenue' ordinal='4' />
            <column datatype='real' name='gross_profit' ordinal='5' />
            <column datatype='integer' name='order_count' ordinal='6' />
            <column datatype='string' name='product_name' ordinal='7' />
            <column datatype='real' name='unit_price' ordinal='8' />
"""
    prod_fields = """
      <column caption='Product Id' datatype='string' name='[product_id]' role='dimension' type='nominal' />
      <column caption='Category' datatype='string' name='[category]' role='dimension' type='nominal' />
      <column caption='Brand' datatype='string' name='[brand]' role='dimension' type='nominal' />
      <column caption='Units Sold' datatype='integer' name='[units_sold]' role='measure' type='quantitative' />
      <column caption='Net Revenue' datatype='real' name='[net_revenue]' role='measure' type='quantitative' />
      <column caption='Gross Profit' datatype='real' name='[gross_profit]' role='measure' type='quantitative' />
      <column caption='Order Count' datatype='integer' name='[order_count]' role='measure' type='quantitative' />
      <column caption='Product Name' datatype='string' name='[product_name]' role='dimension' type='nominal' />
      <column caption='Unit Price' datatype='real' name='[unit_price]' role='measure' type='quantitative' />
"""

    top_stores_sheet = f"""
    <worksheet name='Top Stores by Revenue'>
      <layout-options>
        <title>
          <formatted-text>
            <run fontcolor='#1F2A37' fontname='Arial' fontsize='12' bold='true'>Top Stores by Net Revenue</run>
          </formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{cap}' name='{ds}' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
            <column datatype='string' name='[store_name]' role='dimension' type='nominal' />
            <column datatype='string' name='[region]' role='dimension' type='nominal' />
            <column datatype='real' name='[net_revenue]' role='measure' type='quantitative' />
            <column-instance column='[store_name]' derivation='None' name='[none:store_name:nk]' pivot='key' type='nominal' />
            <column-instance column='[region]' derivation='None' name='[none:region:nk]' pivot='key' type='nominal' />
            <column-instance column='[net_revenue]' derivation='Sum' name='[sum:net_revenue:qk]' pivot='key' type='quantitative' />
          </datasource-dependencies>
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Bar' />
            <encodings>
              <color column='[{ds}].[none:region:nk]' />
            </encodings>
          </pane>
        </panes>
        <rows>[{ds}].[none:store_name:nk]</rows>
        <cols>[{ds}].[sum:net_revenue:qk]</cols>
      </table>
    </worksheet>
"""


    worksheets = [
        calc_kpi_sheet(ds, cap, "KPI Net Revenue", "NET REVENUE", "Calculation_Net_Revenue"),
        calc_kpi_sheet(ds, cap, "KPI Orders", "ORDERS", "Calculation_Orders"),
        calc_kpi_sheet(ds, cap, "KPI AOV", "AOV", "Calculation_AOV"),
        calc_kpi_sheet(ds, cap, "KPI Gross Margin", "GROSS MARGIN %", "Calculation_Gross_Margin_Pct"),
        line_sheet(ds, cap, "Revenue Trend", "Daily Net Revenue Trend", "transaction_date", "net_revenue", "Sum", "sum:net_revenue:qk"),
        bar_sheet(ds, cap, "Revenue by Region", "Net Revenue by Region", "region", "net_revenue", "Sum", "sum:net_revenue:qk", horizontal=True),
        bar_sheet(ds, cap, "Revenue by Store Type", "Net Revenue by Store Type", "store_type", "net_revenue", "Sum", "sum:net_revenue:qk", horizontal=True),
        bar_sheet(ds, cap, "Margin by Region", "Gross Margin % by Region", "region", "Calculation_Gross_Margin_Pct", "User", "usr:Calculation_Gross_Margin_Pct:qk", horizontal=True),
        top_stores_sheet,
        bar_sheet(ds_cat, cap_cat, "Category Revenue", "Net Revenue by Category", "category", "net_revenue", "Sum", "sum:net_revenue:qk", horizontal=True),
        line_sheet(ds_cat, cap_cat, "Category Trend", "Category Net Revenue Trend", "transaction_date", "net_revenue", "Sum", "sum:net_revenue:qk"),
        bar_sheet(ds_ch, cap_ch, "Channel Revenue", "Net Revenue by Channel", "channel", "net_revenue", "Sum", "sum:net_revenue:qk", horizontal=True),
        heatmap_sheet(ds_ch, cap_ch, "Channel Payment Heatmap", "Channel × Payment Method Revenue", "channel", "payment_method", "net_revenue", "Sum", "sum:net_revenue:qk", measure_dtype="real"),
        bar_sheet(ds_prod, cap_prod, "Top Products", "Top Products by Net Revenue", "product_name", "net_revenue", "Sum", "sum:net_revenue:qk", horizontal=True, color_dim="category"),
    ]

    sheet_names = [
        "KPI Net Revenue", "KPI Orders", "KPI AOV", "KPI Gross Margin",
        "Revenue Trend", "Revenue by Region", "Revenue by Store Type", "Margin by Region",
        "Top Stores by Revenue", "Category Revenue", "Category Trend",
        "Channel Revenue", "Channel Payment Heatmap", "Top Products",
    ]

    xml = f"""<?xml version='1.0' encoding='utf-8' ?>
<!-- Retail Sales Report -->
<!-- Built for Tableau Desktop / Tableau Public 2022+ -->
<workbook original-version='18.1' source-build='2022.3.0 (20223.22.0908.1640)' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <document-format-change-manifest>
    <_.fcp.MarkAnimation.true...MarkAnimation />
    <SheetIdentifierTracking />
    <WindowsPersistSimpleIdentifiers />
  </document-format-change-manifest>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>

  <datasources>
    <datasource hasconnection='false' inline='true' name='Parameters' version='18.1'>
      <aliases enabled='yes' />
    </datasource>
{textscan_ds(ds, cap, 'textscan.daily_sales_store', 'mart_daily_sales_by_store.csv', store_cols, store_fields, store_calcs)}
{textscan_ds(ds_cat, cap_cat, 'textscan.daily_sales_category', 'mart_daily_sales_by_category.csv', cat_cols, cat_fields, '')}
{textscan_ds(ds_ch, cap_ch, 'textscan.channel_mix', 'mart_channel_mix.csv', ch_cols, ch_fields, '')}
{textscan_ds(ds_prod, cap_prod, 'textscan.product_perf', 'mart_product_performance.csv', prod_cols, prod_fields, '')}
  </datasources>

  <actions>
    <action caption='Filter by Region' name='[Action_Filter_Region]'>
      <activation auto-clear='true' type='on-select' />
      <source dashboard='1. Overview' type='sheet' worksheet='Revenue by Region' />
      <command command='tsc:tsl-filter'>
        <param name='exclude' value='Revenue by Region' />
        <param name='special-fields' value='all' />
        <param name='target' value='1. Overview' />
      </command>
    </action>
    <action caption='Navigate to Stores' name='[Action_Nav_Stores]'>
      <activation type='on-select' />
      <source dashboard='1. Overview' type='sheet' worksheet='Revenue by Region' />
      <command command='tsc:goto-sheet'>
        <param name='sheet' value='2. Stores and Regions' />
      </command>
    </action>
  </actions>

  <worksheets>
{''.join(worksheets)}
  </worksheets>

  <dashboards>
    <dashboard name='1. Overview'>
      <style>
        <style-rule element='dashboard'>
          <format attr='background-color' value='#F4F6F8' />
        </style-rule>
      </style>
      <size maxheight='900' maxwidth='1400' minheight='900' minwidth='1400' sizing-mode='fixed' />
      <zones>
        <zone h='900' id='100' type-name='layout-basic' w='1400' x='0' y='0'>
          <zone h='50' id='101' type-name='text' w='1360' x='20' y='10'>
            <formatted-text>
              <run fontcolor='#0B3D5C' fontname='Arial' fontsize='18' bold='true'>Retail Sales</run>
              <run fontcolor='#1F2A37' fontname='Arial' fontsize='16' bold='true'>  |  Overview</run>
              <run fontcolor='#5B6B7C' fontname='Arial' fontsize='10'>\nRevenue, orders, AOV, margin — daily trend and regional mix</run>
            </formatted-text>
          </zone>
          <zone h='90' id='102' name='KPI Net Revenue' w='320' x='20' y='70' />
          <zone h='90' id='103' name='KPI Orders' w='320' x='360' y='70' />
          <zone h='90' id='104' name='KPI AOV' w='320' x='700' y='70' />
          <zone h='90' id='105' name='KPI Gross Margin' w='340' x='1040' y='70' />
          <zone h='340' id='106' name='Revenue Trend' w='760' x='20' y='175' />
          <zone h='340' id='107' name='Revenue by Region' w='580' x='800' y='175' />
          <zone h='340' id='108' name='Category Revenue' w='680' x='20' y='530' />
          <zone h='340' id='109' name='Channel Revenue' w='660' x='720' y='530' />
        </zone>
      </zones>
      <devicelayouts />
{simple_id_xml()}
    </dashboard>

    <dashboard name='2. Stores and Regions'>
      <style>
        <style-rule element='dashboard'>
          <format attr='background-color' value='#F4F6F8' />
        </style-rule>
      </style>
      <size maxheight='900' maxwidth='1400' minheight='900' minwidth='1400' sizing-mode='fixed' />
      <zones>
        <zone h='900' id='200' type-name='layout-basic' w='1400' x='0' y='0'>
          <zone h='50' id='201' type-name='text' w='1360' x='20' y='10'>
            <formatted-text>
              <run fontcolor='#0B3D5C' fontname='Arial' fontsize='18' bold='true'>Retail Sales</run>
              <run fontcolor='#1F2A37' fontname='Arial' fontsize='16' bold='true'>  |  Stores and Regions</run>
              <run fontcolor='#5B6B7C' fontname='Arial' fontsize='10'>\nTop stores (parameter-driven), store-type mix, regional margin</run>
            </formatted-text>
          </zone>
          <zone h='400' id='202' name='Top Stores by Revenue' w='700' x='20' y='70' />
          <zone h='400' id='203' name='Revenue by Store Type' w='640' x='740' y='70' />
          <zone h='370' id='204' name='Margin by Region' w='1360' x='20' y='490' />
        </zone>
      </zones>
      <devicelayouts />
{simple_id_xml()}
    </dashboard>

    <dashboard name='3. Trends'>
      <style>
        <style-rule element='dashboard'>
          <format attr='background-color' value='#F4F6F8' />
        </style-rule>
      </style>
      <size maxheight='900' maxwidth='1400' minheight='900' minwidth='1400' sizing-mode='fixed' />
      <zones>
        <zone h='900' id='300' type-name='layout-basic' w='1400' x='0' y='0'>
          <zone h='50' id='301' type-name='text' w='1360' x='20' y='10'>
            <formatted-text>
              <run fontcolor='#0B3D5C' fontname='Arial' fontsize='18' bold='true'>Retail Sales</run>
              <run fontcolor='#1F2A37' fontname='Arial' fontsize='16' bold='true'>  |  Trends</run>
              <run fontcolor='#5B6B7C' fontname='Arial' fontsize='10'>\nCategory trends, channel × payment heatmap, top products</run>
            </formatted-text>
          </zone>
          <zone h='360' id='302' name='Category Trend' w='700' x='20' y='70' />
          <zone h='360' id='303' name='Channel Payment Heatmap' w='640' x='740' y='70' />
          <zone h='400' id='304' name='Top Products' w='1360' x='20' y='450' />
        </zone>
      </zones>
      <devicelayouts />
{simple_id_xml()}
    </dashboard>
  </dashboards>

  <windows source-height='30'>
{sheet_windows_xml(sheet_names)}
    <window class='dashboard' maximized='true' name='1. Overview'>
      <viewpoints>
        <viewpoint name='KPI Net Revenue' />
        <viewpoint name='KPI Orders' />
        <viewpoint name='KPI AOV' />
        <viewpoint name='KPI Gross Margin' />
        <viewpoint name='Revenue Trend' />
        <viewpoint name='Revenue by Region' />
        <viewpoint name='Category Revenue' />
        <viewpoint name='Channel Revenue' />
      </viewpoints>
      <active id='-1' />
    </window>
    <window class='dashboard' name='2. Stores and Regions'>
      <viewpoints>
        <viewpoint name='Top Stores by Revenue' />
        <viewpoint name='Revenue by Store Type' />
        <viewpoint name='Margin by Region' />
      </viewpoints>
      <active id='-1' />
    </window>
    <window class='dashboard' name='3. Trends'>
      <viewpoints>
        <viewpoint name='Category Trend' />
        <viewpoint name='Channel Payment Heatmap' />
        <viewpoint name='Top Products' />
      </viewpoints>
      <active id='-1' />
    </window>
  </windows>
</workbook>
"""
    return xml


def create_service_twb() -> str:
    ds = "federated.service_tickets"
    cap = "Service Performance"

    cols = """
            <column datatype='string' name='ticket_id' ordinal='0' />
            <column datatype='datetime' name='opened_at' ordinal='1' />
            <column datatype='datetime' name='resolved_at' ordinal='2' />
            <column datatype='datetime' name='sla_due_at' ordinal='3' />
            <column datatype='date' name='opened_date' ordinal='4' />
            <column datatype='string' name='status' ordinal='5' />
            <column datatype='string' name='priority' ordinal='6' />
            <column datatype='string' name='reason' ordinal='7' />
            <column datatype='string' name='channel' ordinal='8' />
            <column datatype='string' name='store_id' ordinal='9' />
            <column datatype='string' name='store_name' ordinal='10' />
            <column datatype='string' name='region' ordinal='11' />
            <column datatype='string' name='customer_id' ordinal='12' />
            <column datatype='real' name='csat' ordinal='13' />
            <column datatype='real' name='resolve_hours' ordinal='14' />
            <column datatype='real' name='age_hours' ordinal='15' />
            <column datatype='integer' name='is_open' ordinal='16' />
            <column datatype='string' name='sla_breach' ordinal='17' />
            <column datatype='string' name='sla_status' ordinal='18' />
"""
    fields = """
      <column caption='Ticket Id' datatype='string' name='[ticket_id]' role='dimension' type='nominal' />
      <column caption='Opened At' datatype='datetime' name='[opened_at]' role='dimension' type='ordinal' />
      <column caption='Resolved At' datatype='datetime' name='[resolved_at]' role='dimension' type='ordinal' />
      <column caption='Sla Due At' datatype='datetime' name='[sla_due_at]' role='dimension' type='ordinal' />
      <column caption='Opened Date' datatype='date' name='[opened_date]' role='dimension' type='ordinal' />
      <column caption='Status' datatype='string' name='[status]' role='dimension' type='nominal' />
      <column caption='Priority' datatype='string' name='[priority]' role='dimension' type='nominal' />
      <column caption='Reason' datatype='string' name='[reason]' role='dimension' type='nominal' />
      <column caption='Channel' datatype='string' name='[channel]' role='dimension' type='nominal' />
      <column caption='Store Id' datatype='string' name='[store_id]' role='dimension' type='nominal' />
      <column caption='Store Name' datatype='string' name='[store_name]' role='dimension' type='nominal' />
      <column caption='Region' datatype='string' name='[region]' role='dimension' type='nominal' />
      <column caption='Customer Id' datatype='string' name='[customer_id]' role='dimension' type='nominal' />
      <column caption='Csat' datatype='real' name='[csat]' role='measure' type='quantitative' />
      <column caption='Resolve Hours' datatype='real' name='[resolve_hours]' role='measure' type='quantitative' />
      <column caption='Age Hours' datatype='real' name='[age_hours]' role='measure' type='quantitative' />
      <column caption='Is Open' datatype='integer' name='[is_open]' role='measure' type='quantitative' />
      <column caption='Sla Breach' datatype='string' name='[sla_breach]' role='dimension' type='nominal' />
      <column caption='Sla Status' datatype='string' name='[sla_status]' role='dimension' type='nominal' />
"""
    calcs = """
      <column caption='Ticket Volume' datatype='integer' name='[Calculation_Ticket_Volume]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='COUNTD([ticket_id])' />
      </column>
      <column caption='Avg CSAT' datatype='real' default-format='n#,##0.00' name='[Calculation_Avg_CSAT]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='AVG([csat])' />
      </column>
      <column caption='Within SLA %' datatype='real' default-format='p0.0%' name='[Calculation_Within_SLA_Pct]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM(IF [sla_status]=&quot;within_sla&quot; THEN 1 ELSE 0 END) / NULLIF(SUM(IF [is_open]=0 THEN 1 ELSE 0 END), 0)' />
      </column>
      <column caption='Pending Count' datatype='integer' name='[Calculation_Pending]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM(IF [status]=&quot;pending&quot; OR [status]=&quot;escalated&quot; THEN 1 ELSE 0 END)' />
      </column>
      <column caption='Pending Flag' datatype='integer' name='[Calculation_Pending_Flag]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='IF [status]=&quot;pending&quot; OR [status]=&quot;escalated&quot; THEN 1 ELSE 0 END' />
      </column>
      <column caption='Aging Bucket' datatype='string' name='[Calculation_Aging_Bucket]' role='dimension' type='nominal'>
        <calculation class='tableau' formula='IF [age_hours] &lt; 24 THEN &quot;0-24h&quot; ELSEIF [age_hours] &lt; 48 THEN &quot;24-48h&quot; ELSEIF [age_hours] &lt; 72 THEN &quot;48-72h&quot; ELSEIF [age_hours] &lt; 168 THEN &quot;3-7d&quot; ELSE &quot;7d+&quot; END' />
      </column>
      <column caption='Beyond Aging Threshold' datatype='boolean' name='[Calculation_Beyond_Aging]' role='dimension' type='nominal'>
        <calculation class='tableau' formula='[age_hours] &gt;= [Parameters].[Aging Threshold Hours]' />
      </column>
      <column caption='Avg Resolve Hours' datatype='real' default-format='n#,##0.0' name='[Calculation_Avg_Resolve]' role='measure' type='quantitative'>
        <calculation class='tableau' formula='AVG([resolve_hours])' />
      </column>
"""

    aging_open_sheet = f"""
    <worksheet name='Open Aging Buckets'>
      <layout-options>
        <title>
          <formatted-text>
            <run fontcolor='#1F2A37' fontname='Arial' fontsize='12' bold='true'>Open Ticket Aging Buckets</run>
          </formatted-text>
        </title>
      </layout-options>
      <table>
        <view>
          <datasources>
            <datasource caption='{cap}' name='{ds}' />
            <datasource name='Parameters' />
          </datasources>
          <datasource-dependencies datasource='Parameters'>
            <column caption='Aging Threshold Hours' datatype='integer' name='[Aging Threshold Hours]' param-domain-type='range' role='measure' type='quantitative' value='72'>
              <calculation class='tableau' formula='72' />
              <range granularity='1' max='336' min='24' />
            </column>
          </datasource-dependencies>
          <datasource-dependencies datasource='{ds}'>
            <column datatype='string' name='[Calculation_Aging_Bucket]' role='dimension' type='nominal' />
            <column datatype='integer' name='[is_open]' role='measure' type='quantitative' />
            <column datatype='string' name='[ticket_id]' role='dimension' type='nominal' />
            <column-instance column='[Calculation_Aging_Bucket]' derivation='None' name='[none:Calculation_Aging_Bucket:nk]' pivot='key' type='nominal' />
            <column-instance column='[ticket_id]' derivation='CountD' name='[cd:ticket_id:qk]' pivot='key' type='quantitative' />
            <column-instance column='[is_open]' derivation='Sum' name='[sum:is_open:qk]' pivot='key' type='quantitative' />
          </datasource-dependencies>
          <filter class='quantitative' column='[{ds}].[sum:is_open:qk]' include-null='true'>
            <min>1</min>
          </filter>
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='Bar' />
          </pane>
        </panes>
        <rows>[{ds}].[cd:ticket_id:qk]</rows>
        <cols>[{ds}].[none:Calculation_Aging_Bucket:nk]</cols>
      </table>
    </worksheet>
"""

    worksheets = [
        calc_kpi_sheet(ds, cap, "KPI Ticket Volume", "TICKET VOLUME", "Calculation_Ticket_Volume"),
        calc_kpi_sheet(ds, cap, "KPI Avg CSAT", "AVG CSAT", "Calculation_Avg_CSAT"),
        calc_kpi_sheet(ds, cap, "KPI Within SLA", "WITHIN SLA %", "Calculation_Within_SLA_Pct"),
        calc_kpi_sheet(ds, cap, "KPI Pending", "PENDING / ESCALATED", "Calculation_Pending"),
        line_sheet(ds, cap, "Ticket Volume Trend", "Ticket Volume by Opened Date", "opened_date", "is_open", "Count", "cnt:is_open:qk", measure_dtype="integer").replace(
            """<column datatype='integer' name='[is_open]' role='measure' type='quantitative' />
            <column-instance column='[opened_date]' derivation='None' name='[none:opened_date:ok]' pivot='key' type='ordinal' />
            <column-instance column='[is_open]' derivation='Count' name='[cnt:is_open:qk]' pivot='key' type='quantitative' />""",
            """<column datatype='string' name='[ticket_id]' role='dimension' type='nominal' />
            <column-instance column='[opened_date]' derivation='None' name='[none:opened_date:ok]' pivot='key' type='ordinal' />
            <column-instance column='[ticket_id]' derivation='CountD' name='[cd:ticket_id:qk]' pivot='key' type='quantitative' />""",
        ).replace("[cnt:is_open:qk]", "[cd:ticket_id:qk]"),
        bar_sheet(ds, cap, "Reason Mix", "Tickets by Reason", "reason", "is_open", "Count", "cnt:is_open:qk", horizontal=True, measure_dtype="integer").replace(
            """<column datatype='integer' name='[is_open]' role='measure' type='quantitative' />
            <column-instance column='[reason]' derivation='None' name='[none:reason:nk]' pivot='key' type='nominal' />
            <column-instance column='[is_open]' derivation='Count' name='[cnt:is_open:qk]' pivot='key' type='quantitative' />""",
            """<column datatype='string' name='[ticket_id]' role='dimension' type='nominal' />
            <column-instance column='[reason]' derivation='None' name='[none:reason:nk]' pivot='key' type='nominal' />
            <column-instance column='[ticket_id]' derivation='CountD' name='[cd:ticket_id:qk]' pivot='key' type='quantitative' />""",
        ).replace("[cnt:is_open:qk]", "[cd:ticket_id:qk]"),
        bar_sheet(ds, cap, "Channel Mix", "Tickets by Channel", "channel", "is_open", "Count", "cnt:is_open:qk", horizontal=True, measure_dtype="integer").replace(
            """<column datatype='integer' name='[is_open]' role='measure' type='quantitative' />
            <column-instance column='[channel]' derivation='None' name='[none:channel:nk]' pivot='key' type='nominal' />
            <column-instance column='[is_open]' derivation='Count' name='[cnt:is_open:qk]' pivot='key' type='quantitative' />""",
            """<column datatype='string' name='[ticket_id]' role='dimension' type='nominal' />
            <column-instance column='[channel]' derivation='None' name='[none:channel:nk]' pivot='key' type='nominal' />
            <column-instance column='[ticket_id]' derivation='CountD' name='[cd:ticket_id:qk]' pivot='key' type='quantitative' />""",
        ).replace("[cnt:is_open:qk]", "[cd:ticket_id:qk]"),
        bar_sheet(ds, cap, "SLA Status Mix", "SLA Status Mix (Within / Beyond / Pending)", "sla_status", "is_open", "Count", "cnt:is_open:qk", horizontal=True, measure_dtype="integer").replace(
            """<column datatype='integer' name='[is_open]' role='measure' type='quantitative' />
            <column-instance column='[sla_status]' derivation='None' name='[none:sla_status:nk]' pivot='key' type='nominal' />
            <column-instance column='[is_open]' derivation='Count' name='[cnt:is_open:qk]' pivot='key' type='quantitative' />""",
            """<column datatype='string' name='[ticket_id]' role='dimension' type='nominal' />
            <column-instance column='[sla_status]' derivation='None' name='[none:sla_status:nk]' pivot='key' type='nominal' />
            <column-instance column='[ticket_id]' derivation='CountD' name='[cd:ticket_id:qk]' pivot='key' type='quantitative' />""",
        ).replace("[cnt:is_open:qk]", "[cd:ticket_id:qk]"),
        bar_sheet(ds, cap, "Resolve by Priority", "Avg Resolve Hours by Priority", "priority", "Calculation_Avg_Resolve", "User", "usr:Calculation_Avg_Resolve:qk", horizontal=True),
        heatmap_sheet(ds, cap, "Breach by Channel", "Ticket Volume Heatmap: Channel × Priority", "channel", "priority", "is_open", "Count", "cnt:is_open:qk").replace(
            """<column datatype='integer' name='[is_open]' role='measure' type='quantitative' />
            <column-instance column='[channel]' derivation='None' name='[none:channel:nk]' pivot='key' type='nominal' />
            <column-instance column='[priority]' derivation='None' name='[none:priority:nk]' pivot='key' type='nominal' />
            <column-instance column='[is_open]' derivation='Count' name='[cnt:is_open:qk]' pivot='key' type='quantitative' />""",
            """<column datatype='string' name='[ticket_id]' role='dimension' type='nominal' />
            <column-instance column='[channel]' derivation='None' name='[none:channel:nk]' pivot='key' type='nominal' />
            <column-instance column='[priority]' derivation='None' name='[none:priority:nk]' pivot='key' type='nominal' />
            <column-instance column='[ticket_id]' derivation='CountD' name='[cd:ticket_id:qk]' pivot='key' type='quantitative' />""",
        ).replace("[cnt:is_open:qk]", "[cd:ticket_id:qk]"),
        calc_kpi_sheet(ds, cap, "KPI Avg Resolve", "AVG RESOLVE (HRS)", "Calculation_Avg_Resolve"),
        bar_sheet(ds, cap, "Within SLA by Region", "Within-SLA Ticket Share Proxy by Region", "region", "Calculation_Within_SLA_Pct", "User", "usr:Calculation_Within_SLA_Pct:qk", horizontal=True),
        aging_open_sheet,
        bar_sheet(ds, cap, "Open by Priority", "Open Backlog by Priority", "priority", "is_open", "Sum", "sum:is_open:qk", horizontal=True, measure_dtype="integer"),
        bar_sheet(ds, cap, "Open Reasons", "Open Tickets by Reason", "reason", "is_open", "Sum", "sum:is_open:qk", horizontal=True, measure_dtype="integer"),
        bar_sheet(ds, cap, "CSAT by Channel", "Avg CSAT by Channel", "channel", "Calculation_Avg_CSAT", "User", "usr:Calculation_Avg_CSAT:qk", horizontal=True),
    ]

    sheet_names = [
        "KPI Ticket Volume", "KPI Avg CSAT", "KPI Within SLA", "KPI Pending",
        "Ticket Volume Trend", "Reason Mix", "Channel Mix", "SLA Status Mix",
        "Resolve by Priority", "Breach by Channel", "KPI Avg Resolve",
        "Within SLA by Region", "Open Aging Buckets", "Open by Priority",
        "Open Reasons", "CSAT by Channel",
    ]

    xml = f"""<?xml version='1.0' encoding='utf-8' ?>
<!-- Retail Customer Satisfaction and Service Report -->
<!-- Built for Tableau Desktop / Tableau Public 2022+ -->
<workbook original-version='18.1' source-build='2022.3.0 (20223.22.0908.1640)' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <document-format-change-manifest>
    <_.fcp.MarkAnimation.true...MarkAnimation />
    <SheetIdentifierTracking />
    <WindowsPersistSimpleIdentifiers />
  </document-format-change-manifest>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>

  <datasources>
    <datasource hasconnection='false' inline='true' name='Parameters' version='18.1'>
      <aliases enabled='yes' />
      <column caption='Aging Threshold Hours' datatype='integer' name='[Aging Threshold Hours]' param-domain-type='range' role='measure' type='quantitative' value='72'>
        <calculation class='tableau' formula='72' />
        <range granularity='1' max='336' min='24' />
      </column>
    </datasource>
{textscan_ds(ds, cap, 'textscan.service_tickets', 'mart_service_performance.csv', cols, fields, calcs)}
  </datasources>

  <actions>
    <action caption='Filter by Reason' name='[Action_Filter_Reason]'>
      <activation auto-clear='true' type='on-select' />
      <source dashboard='1. Overview' type='sheet' worksheet='Reason Mix' />
      <command command='tsc:tsl-filter'>
        <param name='exclude' value='Reason Mix' />
        <param name='special-fields' value='all' />
        <param name='target' value='1. Overview' />
      </command>
    </action>
    <action caption='Filter by SLA Status' name='[Action_Filter_SLA]'>
      <activation auto-clear='true' type='on-select' />
      <source dashboard='2. SLA Performance' type='sheet' worksheet='SLA Status Mix' />
      <command command='tsc:tsl-filter'>
        <param name='exclude' value='SLA Status Mix' />
        <param name='special-fields' value='all' />
        <param name='target' value='2. SLA Performance' />
      </command>
    </action>
  </actions>

  <worksheets>
{''.join(worksheets)}
  </worksheets>

  <dashboards>
    <dashboard name='1. Overview'>
      <style>
        <style-rule element='dashboard'>
          <format attr='background-color' value='#F4F6F8' />
        </style-rule>
      </style>
      <size maxheight='900' maxwidth='1400' minheight='900' minwidth='1400' sizing-mode='fixed' />
      <zones>
        <zone h='900' id='100' type-name='layout-basic' w='1400' x='0' y='0'>
          <zone h='50' id='101' type-name='text' w='1360' x='20' y='10'>
            <formatted-text>
              <run fontcolor='#0B3D5C' fontname='Arial' fontsize='18' bold='true'>Customer Satisfaction and Service</run>
              <run fontcolor='#1F2A37' fontname='Arial' fontsize='16' bold='true'>  |  Overview</run>
              <run fontcolor='#5B6B7C' fontname='Arial' fontsize='10'>\nTicket volume, CSAT, within-SLA rate, pending — reason and channel mix</run>
            </formatted-text>
          </zone>
          <zone h='90' id='102' name='KPI Ticket Volume' w='320' x='20' y='70' />
          <zone h='90' id='103' name='KPI Avg CSAT' w='320' x='360' y='70' />
          <zone h='90' id='104' name='KPI Within SLA' w='320' x='700' y='70' />
          <zone h='90' id='105' name='KPI Pending' w='340' x='1040' y='70' />
          <zone h='340' id='106' name='Ticket Volume Trend' w='700' x='20' y='175' />
          <zone h='340' id='107' name='CSAT by Channel' w='640' x='740' y='175' />
          <zone h='340' id='108' name='Reason Mix' w='680' x='20' y='530' />
          <zone h='340' id='109' name='Channel Mix' w='660' x='720' y='530' />
        </zone>
      </zones>
      <devicelayouts />
{simple_id_xml()}
    </dashboard>

    <dashboard name='2. SLA Performance'>
      <style>
        <style-rule element='dashboard'>
          <format attr='background-color' value='#F4F6F8' />
        </style-rule>
      </style>
      <size maxheight='900' maxwidth='1400' minheight='900' minwidth='1400' sizing-mode='fixed' />
      <zones>
        <zone h='900' id='200' type-name='layout-basic' w='1400' x='0' y='0'>
          <zone h='50' id='201' type-name='text' w='1360' x='20' y='10'>
            <formatted-text>
              <run fontcolor='#0B3D5C' fontname='Arial' fontsize='18' bold='true'>Customer Satisfaction and Service</run>
              <run fontcolor='#1F2A37' fontname='Arial' fontsize='16' bold='true'>  |  SLA Performance</run>
              <run fontcolor='#5B6B7C' fontname='Arial' fontsize='10'>\nWithin / beyond / pending SLA, resolve hours by priority, breach patterns, regional attainment</run>
            </formatted-text>
          </zone>
          <zone h='360' id='202' name='SLA Status Mix' w='460' x='20' y='70' />
          <zone h='360' id='203' name='Resolve by Priority' w='440' x='500' y='70' />
          <zone h='360' id='204' name='KPI Avg Resolve' w='420' x='960' y='70' />
          <zone h='400' id='205' name='Breach by Channel' w='700' x='20' y='450' />
          <zone h='400' id='206' name='Within SLA by Region' w='640' x='740' y='450' />
        </zone>
      </zones>
      <devicelayouts />
{simple_id_xml()}
    </dashboard>

    <dashboard name='3. Pending and Aging'>
      <style>
        <style-rule element='dashboard'>
          <format attr='background-color' value='#F4F6F8' />
        </style-rule>
      </style>
      <size maxheight='900' maxwidth='1400' minheight='900' minwidth='1400' sizing-mode='fixed' />
      <zones>
        <zone h='900' id='300' type-name='layout-basic' w='1400' x='0' y='0'>
          <zone h='50' id='301' type-name='text' w='1360' x='20' y='10'>
            <formatted-text>
              <run fontcolor='#0B3D5C' fontname='Arial' fontsize='18' bold='true'>Customer Satisfaction and Service</run>
              <run fontcolor='#1F2A37' fontname='Arial' fontsize='16' bold='true'>  |  Pending and Aging</run>
              <run fontcolor='#5B6B7C' fontname='Arial' fontsize='10'>\nOpen-queue age buckets (Aging Threshold Hours parameter), priority backlog, open reasons</run>
            </formatted-text>
          </zone>
          <zone h='400' id='302' name='Open Aging Buckets' w='700' x='20' y='70' />
          <zone h='400' id='303' name='Open by Priority' w='640' x='740' y='70' />
          <zone h='370' id='304' name='Open Reasons' w='1360' x='20' y='490' />
        </zone>
      </zones>
      <devicelayouts />
{simple_id_xml()}
    </dashboard>
  </dashboards>

  <windows source-height='30'>
{sheet_windows_xml(sheet_names)}
    <window class='dashboard' maximized='true' name='1. Overview'>
      <viewpoints>
        <viewpoint name='KPI Ticket Volume' />
        <viewpoint name='KPI Avg CSAT' />
        <viewpoint name='KPI Within SLA' />
        <viewpoint name='KPI Pending' />
        <viewpoint name='Ticket Volume Trend' />
        <viewpoint name='CSAT by Channel' />
        <viewpoint name='Reason Mix' />
        <viewpoint name='Channel Mix' />
      </viewpoints>
      <active id='-1' />
    </window>
    <window class='dashboard' name='2. SLA Performance'>
      <viewpoints>
        <viewpoint name='SLA Status Mix' />
        <viewpoint name='Resolve by Priority' />
        <viewpoint name='KPI Avg Resolve' />
        <viewpoint name='Breach by Channel' />
        <viewpoint name='Within SLA by Region' />
      </viewpoints>
      <active id='-1' />
    </window>
    <window class='dashboard' name='3. Pending and Aging'>
      <viewpoints>
        <viewpoint name='Open Aging Buckets' />
        <viewpoint name='Open by Priority' />
        <viewpoint name='Open Reasons' />
      </viewpoints>
      <active id='-1' />
    </window>
  </windows>
</workbook>
"""
    return xml



def _clone(el: ET.Element) -> ET.Element:
    return ET.fromstring(ET.tostring(el, encoding="unicode"))


def _dashboard_xml(
    name: str,
    title_main: str,
    title_sub: str,
    subtitle: str,
    zones: list[tuple[str, int, int, int, int]],
    banner_id: int = 1,
) -> str:
    """zones: list of (sheet_name, x, y, w, h). Fixed 1400x900 canvas."""
    zone_lines = [
        f"          <zone h='50' id='{banner_id}' type-name='text' w='1360' x='20' y='10'>",
        "            <formatted-text>",
        f"              <run fontcolor='#0B3D5C' fontname='Arial' fontsize='18' bold='true'>{esc(title_main)}</run>",
        f"              <run fontcolor='#1F2A37' fontname='Arial' fontsize='16' bold='true'>  |  {esc(title_sub)}</run>",
        f"              <run fontcolor='#5B6B7C' fontname='Arial' fontsize='10'>\\n{esc(subtitle)}</run>",
        "            </formatted-text>",
        "          </zone>",
    ]
    zid = banner_id + 1
    for sheet, x, y, w, h in zones:
        zone_lines.append(
            f"          <zone h='{h}' id='{zid}' name='{esc(sheet)}' w='{w}' x='{x}' y='{y}' />"
        )
        zid += 1
    zones_body = "\n".join(zone_lines)
    return f"""
    <dashboard name='{esc(name)}'>
      <style>
        <style-rule element='dashboard'>
          <format attr='background-color' value='#F4F6F8' />
        </style-rule>
      </style>
      <size maxheight='900' maxwidth='1400' minheight='900' minwidth='1400' sizing-mode='fixed' />
      <zones>
        <zone h='900' id='{banner_id - 1 if banner_id > 0 else 0}' type-name='layout-basic' w='1400' x='0' y='0'>
{zones_body}
        </zone>
      </zones>
      <devicelayouts />
{simple_id_xml()}
    </dashboard>
"""


def create_ops_twb() -> str:
    """Combined Retail Ops suite: two primary dashboards (Sales, Service).

    Reuses worksheets/datasources from the sales + service builders.
    Dashboard windows are listed first (Sales maximized). Worksheet tabs stay
    visible — hiding them previously caused Tableau Desktop to discard UI.
    """
    sales_root = ET.fromstring(create_sales_twb())
    service_root = ET.fromstring(create_service_twb())

    # --- Parameters: merge sales Parameters + Aging Threshold Hours ---
    params = _clone(sales_root.find("./datasources/datasource[@name='Parameters']"))
    svc_params = service_root.find("./datasources/datasource[@name='Parameters']")
    for col in list(svc_params.findall("column")):
        name = col.get("name")
        if params.find(f"./column[@name='{name}']") is None:
            params.append(_clone(col))

    # --- Datasources: Parameters + all non-Parameter sources from both ---
    ds_xml_parts = [ET.tostring(params, encoding="unicode")]
    seen_ds = {"Parameters"}
    for root in (sales_root, service_root):
        for ds in root.findall("./datasources/datasource"):
            name = ds.get("name")
            if name in seen_ds:
                continue
            seen_ds.add(name)
            ds_xml_parts.append(ET.tostring(ds, encoding="unicode"))

    # --- Worksheets: all unique by name (sales first, then service) ---
    ws_xml_parts: list[str] = []
    sheet_names: list[str] = []
    seen_ws: set[str] = set()
    for root in (sales_root, service_root):
        for ws in root.findall("./worksheets/worksheet"):
            name = ws.get("name")
            if name in seen_ws:
                continue
            seen_ws.add(name)
            sheet_names.append(name)
            # Drop trailing simple-id; ensure_content_models will re-add braced ones
            sid = ws.find("simple-id")
            if sid is not None:
                ws.remove(sid)
            ws_xml_parts.append(ET.tostring(ws, encoding="unicode"))

    # Reuse proven Overview dashboards from the standalones (known to render in Desktop),
    # renamed to Sales / Service. Avoid inventing new zone trees Tableau may reject.
    def _overview_as(root: ET.Element, new_name: str, title_main: str, title_sub: str, subtitle: str) -> str:
        dash = _clone(root.find("./dashboards/dashboard[@name='1. Overview']"))
        dash.set("name", new_name)
        # Drop simple-id / datasources / filled device layouts; ensure_content_models re-adds them
        for tag in ("simple-id", "datasources"):
            el = dash.find(tag)
            if el is not None:
                dash.remove(el)
        dl = dash.find("devicelayouts")
        if dl is not None:
            for child in list(dl):
                dl.remove(child)
        # Refresh banner text runs if present
        runs = dash.findall(".//zone[@type-name='text']/formatted-text/run")
        if len(runs) >= 3:
            runs[0].text = title_main
            runs[1].text = f"  |  {title_sub}"
            runs[2].text = "\n" + subtitle
        # Strip trailing whitespace-only text nodes issues by re-serializing
        return ET.tostring(dash, encoding="unicode")

    sales_dash = _overview_as(
        sales_root,
        "Sales",
        "Retail Ops",
        "Sales",
        "Net revenue, orders, AOV, margin — trend, region, category, channel",
    )
    service_dash = _overview_as(
        service_root,
        "Service",
        "Retail Ops",
        "Service & SLA",
        "Ticket volume, CSAT, within-SLA, pending — trend, reason, channel mix",
    )

    # Zone names referenced by the Overview layouts (for viewpoints)
    sales_zones = [
        (z.get("name"),)
        for z in ET.fromstring(f"<d>{sales_dash}</d>").find("dashboard").findall(".//zone")
        if z.get("name")
    ]
    service_zones = [
        (z.get("name"),)
        for z in ET.fromstring(f"<d>{service_dash}</d>").find("dashboard").findall(".//zone")
        if z.get("name")
    ]

    actions = """
  <actions>
    <action caption='Filter Sales by Region' name='[Action_Ops_Filter_Region]'>
      <activation auto-clear='true' type='on-select' />
      <source dashboard='Sales' type='sheet' worksheet='Revenue by Region' />
      <command command='tsc:tsl-filter'>
        <param name='exclude' value='Revenue by Region' />
        <param name='special-fields' value='all' />
        <param name='target' value='Sales' />
      </command>
    </action>
    <action caption='Filter Service by Reason' name='[Action_Ops_Filter_Reason]'>
      <activation auto-clear='true' type='on-select' />
      <source dashboard='Service' type='sheet' worksheet='Reason Mix' />
      <command command='tsc:tsl-filter'>
        <param name='exclude' value='Reason Mix' />
        <param name='special-fields' value='all' />
        <param name='target' value='Service' />
      </command>
    </action>
  </actions>
"""

    sales_views = "\n".join(
        f"        <viewpoint name='{esc(n)}' />"
        for n, *_ in sales_zones
    )
    service_views = "\n".join(
        f"        <viewpoint name='{esc(n)}' />"
        for n, *_ in service_zones
    )

    xml = f"""<?xml version='1.0' encoding='utf-8' ?>
<!-- Retail Ops Dashboard — Sales + Service (two-page suite) -->
<!-- Built for Tableau Desktop / Tableau Public 2022+ -->
<workbook original-version='18.1' source-build='2022.3.0 (20223.22.0908.1640)' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <document-format-change-manifest>
    <_.fcp.MarkAnimation.true...MarkAnimation />
    <SheetIdentifierTracking />
    <WindowsPersistSimpleIdentifiers />
  </document-format-change-manifest>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>

  <datasources>
{''.join(ds_xml_parts)}
  </datasources>
{actions}
  <worksheets>
{''.join(ws_xml_parts)}
  </worksheets>

  <dashboards>
{sales_dash}
{service_dash}
  </dashboards>

  <windows source-height='30'>
    <window class='dashboard' maximized='true' name='Sales'>
      <viewpoints>
{sales_views}
      </viewpoints>
      <active id='-1' />
    </window>
    <window class='dashboard' name='Service'>
      <viewpoints>
{service_views}
      </viewpoints>
      <active id='-1' />
    </window>
{sheet_windows_xml(sheet_names, hidden=False)}
  </windows>
</workbook>
"""
    return xml




def reorder_windows_dashboards_first(xml: str) -> str:
    """Put dashboard <window> entries first; keep the first dashboard maximized."""
    root = ET.fromstring(xml)
    windows_el = root.find("./windows")
    if windows_el is None:
        return xml
    dash_wins = [w for w in list(windows_el) if w.get("class") == "dashboard"]
    sheet_wins = [w for w in list(windows_el) if w.get("class") != "dashboard"]
    for w in list(windows_el):
        windows_el.remove(w)
    for i, w in enumerate(dash_wins):
        if i == 0:
            w.set("maximized", "true")
        elif "maximized" in w.attrib:
            del w.attrib["maximized"]
        windows_el.append(w)
    for w in sheet_wins:
        if "hidden" in w.attrib:
            del w.attrib["hidden"]
        windows_el.append(w)
    ET.register_namespace("user", "http://www.tableausoftware.com/xml/user")
    out = ET.tostring(root, encoding="unicode")
    if not out.startswith("<?xml"):
        out = "<?xml version='1.0' encoding='utf-8' ?>\n" + out
    return out


def package_twbx(twb_path: Path, twbx_path: Path, csv_files: list[Path], hyper_files: list[Path]) -> None:
    if twbx_path.exists():
        twbx_path.unlink()
    with zipfile.ZipFile(twbx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(twb_path, arcname=twb_path.name)
        for csv_path in csv_files:
            zf.write(csv_path, arcname=f"Data/Datasources/{csv_path.name}")
            zf.write(csv_path, arcname=csv_path.name)
            zf.write(csv_path, arcname=f"Data/{csv_path.name}")
        for hyper_path in hyper_files:
            if hyper_path.exists():
                zf.write(hyper_path, arcname=f"Data/Extracts/{hyper_path.name}")


def build_one(name: str, xml: str, csvs: list[str], hypers: list[str]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    twb_path = OUT / f"{name}.twb"
    twbx_path = OUT / f"{name}.twbx"
    root = ET.fromstring(xml)
    ensure_content_models(root)
    ET.register_namespace("user", "http://www.tableausoftware.com/xml/user")
    xml_out = ET.tostring(root, encoding="unicode")
    if not xml_out.startswith("<?xml"):
        xml_out = "<?xml version='1.0' encoding='utf-8' ?>\n" + xml_out
    ET.fromstring(xml_out)
    # Validate content model presence
    root2 = ET.fromstring(xml_out)
    for ws in root2.findall("./worksheets/worksheet"):
        if ws.find("simple-id") is None:
            raise SystemExit(f"worksheet missing simple-id: {ws.get('name')}")
    ws_names = {ws.get("name") for ws in root2.findall("./worksheets/worksheet")}
    for dash in root2.findall("./dashboards/dashboard"):
        tags = [c.tag for c in list(dash)]
        for req in ("datasources", "zones", "devicelayouts", "simple-id"):
            if req not in tags:
                raise SystemExit(f"dashboard {dash.get('name')} missing {req}; has {tags}")
        # order checks: datasources before zones, zones before devicelayouts, simple-id last
        if tags.index("datasources") > tags.index("zones"):
            raise SystemExit(f"dashboard {dash.get('name')}: datasources must precede zones")
        if tags.index("devicelayouts") < tags.index("zones"):
            raise SystemExit(f"dashboard {dash.get('name')}: devicelayouts must follow zones")
        dl = dash.find("devicelayouts")
        if dl is None or dl.find("devicelayout[@name='Desktop']") is None:
            raise SystemExit(f"dashboard {dash.get('name')}: missing Desktop device layout")
        for zone in dash.findall(".//zone"):
            zname = zone.get("name")
            if zname and zname not in ws_names and zone.get("type-name") not in ("layout-basic", "text", "filter", "legend", "paramctrl", None):
                # named worksheet zones must reference real worksheets
                if zone.get("type-name") is None and zname not in ws_names:
                    raise SystemExit(f"dashboard {dash.get('name')}: zone references unknown worksheet {zname!r}")
            if zname and zone.get("type-name") is None and zname not in ws_names:
                raise SystemExit(f"dashboard {dash.get('name')}: zone references unknown worksheet {zname!r}")
    for sid in root2.findall(".//simple-id"):
        u = sid.get("uuid") or ""
        if not (u.startswith("{") and u.endswith("}")):
            raise SystemExit(f"unbraced simple-id uuid: {u!r}")
    twb_path.write_text(xml_out, encoding="utf-8")
    print(f"Wrote {twb_path} ({twb_path.stat().st_size} bytes)")
    package_twbx(
        twb_path,
        twbx_path,
        [MARTS / c for c in csvs],
        [EXTRACTS / h for h in hypers],
    )
    print(f"Wrote {twbx_path} ({twbx_path.stat().st_size} bytes)")
    with zipfile.ZipFile(twbx_path, "r") as zf:
        print(f"TWBX contents ({name}):")
        for info in zf.infolist():
            print(f"  {info.filename:55s} {info.file_size:10d}")
    return twbx_path


def main() -> None:
    sales_csvs = [
        "mart_daily_sales_by_store.csv",
        "mart_daily_sales_by_category.csv",
        "mart_channel_mix.csv",
        "mart_product_performance.csv",
    ]
    sales_hypers = ["daily_sales_by_store.hyper"]
    service_csvs = ["mart_service_performance.csv"]
    service_hypers = ["service_performance.hyper"]
    ops_csvs = sales_csvs + service_csvs
    ops_hypers = sales_hypers + service_hypers

    # Combined Ops v3 — dashboards first, worksheets visible (no hidden=true)
    build_one("Retail_Ops_Dashboard_v3", create_ops_twb(), ops_csvs, ops_hypers)
    # Keep non-versioned alias in sync for older README links
    build_one("Retail_Ops_Dashboard", create_ops_twb(), ops_csvs, ops_hypers)

    # Reliable single-subject packs: open on Overview dashboard tab
    build_one(
        "Retail_Sales_Dashboard_v3",
        reorder_windows_dashboards_first(create_sales_twb()),
        sales_csvs,
        sales_hypers,
    )
    build_one(
        "Retail_Service_Dashboard_v3",
        reorder_windows_dashboards_first(create_service_twb()),
        service_csvs,
        service_hypers,
    )

    # Legacy multi-page reports (still rebuilt)
    build_one("Retail_Sales_Report", create_sales_twb(), sales_csvs, sales_hypers)
    build_one(
        "Retail_Service_Satisfaction_Report",
        create_service_twb(),
        service_csvs,
        service_hypers,
    )


if __name__ == "__main__":
    main()
