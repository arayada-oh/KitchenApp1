import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- 1. ตั้งค่าหน้าเว็บ Streamlit ---
st.set_page_config(
    page_title="ระบบเช็คสต็อกของในครัว",
    page_icon="🍳",
    layout="wide"
)

# 1. กำหนด Scope เดิมที่คุณใช้งานอยู่
scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
# 2. ดึงข้อมูลจาก st.secrets ของ Streamlit Cloud
def init_connection():
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    else:
        # เผื่อกรณีรันบนคอมตัวเอง (ถ้ายังอยากใช้ไฟล์ credentials.json แบบเดิม)
        from oauth2client.service_account import ServiceAccountCredentials
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

    client = gspread.authorize(creds)
    return client


# เชื่อมต่อฐานข้อมูล
try:
    client = init_connection()
    # ชื่อไฟล์ Google Sheets ต้องตรงกับที่คุณสร้าง
    SPREADSHEET_ID = "1-ecxPbmWEOClLpBbUVyRQW8iNNan9Lbk-s3oxwHoqC8"
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
   #ชีทคลังวัตถุดิบหลัก 
    sheet = spreadsheet.worksheet("IV")
except Exception as e:
    st.error(f"⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {e}")
    st.info("คำแนะนำ: ตรวจสอบว่าแชร์อีเมล Service Account ไปยัง Google Sheet หรือยัง และชื่อไฟล์ถูกต้องไหม")
    st.stop()

# ฟังก์ชันดึงข้อมูลแปลงเป็น DataFrame
# ฟังก์ชันดึงข้อมูลแปลงเป็น DataFrame
def load_data():
    try:
        data = sheet.get_all_records()
        if not data:
            # ถ้าตารางว่างเปล่า ให้คืนค่า DataFrame เปล่าที่มีหัวคอลัมน์เตรียมไว้
            return pd.DataFrame(columns=['ItemCode', 'วัตถุดิบ','In Use', 'Stock', 'Unit', 'Price', 'storage_zone', 'storage_slot', 'Category'])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"⚠️ เกิดข้อผิดพลาดในการดึงข้อมูล (เช็คว่าแถวที่ 1 ใน Google Sheet มีหัวคอลัมน์ครบถ้วนหรือไม่): {e}")
        return pd.DataFrame()

# ฟังก์ชันอัพเดตข้อมูลกลับไปยัง Google Sheets
def update_sheet_data(df):
    try:
        sheet.clear()
        # แปลงข้อมูลทั้งหมดรวมหัวตารางให้อยู่ในรูป List พร้อมอัปเดต
        set_data = [df.columns.values.tolist()] + df.values.tolist()
        sheet.update(range_name='A1', values=set_data)
    except Exception as e:
        st.error(f"⚠️ เกิดข้อผิดพลาดในการบันทึกข้อมูลลง Google Sheets: {e}")

# โหลดข้อมูลเก็บไว้ในตัวแปร
df_stock = load_data()

# --- 3. จัดการตะกร้าสินค้าใน Session State ---
if 'shopping_cart' not in st.session_state:
    st.session_state.shopping_cart = {}

# --- 4. เมนูนำทางด้านข้าง (Sidebar) ---
st.sidebar.title("🍳 เมนูจัดการครัว")
menu = st.sidebar.radio(
    "เลือกหน้าการใช้งาน:", 
    ["🏠 หน้าหลัก", "🔍 ค้นหาวัตถุดิบ", "🛒 รายการที่ต้องซื้อ (Shopping Cart)", "📦 อัพเดตสต็อกสินค้า"]
)

# ==========================================
# 🏠 หน้าหลัก (Home)
# ==========================================
if menu == "🏠 หน้าหลัก":
    st.title("🏡 ยินดีต้อนรับสู่ระบบจัดการของในครัว")
    st.write("เช็คสต็อกวัตถุดิบ ดูของหมด และวางแผนซื้อของเข้าบ้านได้ง่ายๆ ผ่านหน้าจอของคุณ")
    
    st.markdown("---")
    st.subheader("📊 สรุปสถานะคลังสินค้าเบื้องต้น")
    
    if not df_stock.empty:
        total_items = len(df_stock)
        # เช็คสินค้าที่จำนวนน้อยกว่าหรือเท่ากับ 0
        out_of_stock = len(df_stock[df_stock['Stock'] <= 0])
        
        col1, col2 = st.columns(2)
        col1.metric("จำนวนวัตถุดิบทั้งหมด", f"{total_items} รายการ")
        col2.metric("สินค้าที่หมด (ต้องซื้อ)", f"{out_of_stock} รายการ", delta=-out_of_stock, delta_color="inverse")
    else:
        st.warning("ยังไม่มีข้อมูลวัตถุดิบใน Google Sheets")

# ==========================================
# 🔍 หน้าค้นหาวัตถุดิบ
# ==========================================
elif menu == "🔍 ค้นหาวัตถุดิบ":
    st.title("🔍 ค้นหาวัตถุดิบในครัว")
    
    search_query = st.text_input("พิมพ์ชื่อวัตถุดิบ หรือหมวดหมู่ที่ต้องการค้นหา:")
    
    if not df_stock.empty:
        if search_query:
            filtered_df = df_stock[
                df_stock['วัตถุดิบ'].astype(str).str.contains(search_query, case=False, na=False) |
                df_stock['Category'].astype(str).str.contains(search_query, case=False, na=False)
            ]
        else:
            filtered_df = df_stock

        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.warning("ไม่พบข้อมูลในระบบ")

# ==========================================
# 🛒 หน้าเช็คของทั้งหมด & ตะกร้าสินค้า
# ==========================================
elif menu == "🛒 รายการที่ต้องซื้อ (Shopping Cart)":
    st.title("🛒 เช็ครายการของ & ตะกร้าสินค้า")
    
    tab1, tab2 = st.tabs(["📦 รายการวัตถุดิบทั้งหมด", "🛍️ ตะกร้าสินค้า"])
    
    with tab1:
        st.subheader("สถานะวัตถุดิบในครัว")
        
        if not df_stock.empty:
            # สร้างตัวเลือกโหมดการแสดงผล (ใช้ st.radio แบบแนวนอน)
            view_mode = st.radio(
                "เลือกการแสดงผล:", 
                ["📋 แสดงทั้งหมด", "❌ เฉพาะรายการที่หมดแล้ว (Stock = 0)"], 
                horizontal=True
            )
            
            st.divider()
            
            # กรองข้อมูลตามโหมดที่เลือก
            if view_mode == "❌ เฉพาะรายการที่หมดแล้ว (Stock = 0)":
                # แปลงค่า Stock เป็นตัวเลขเพื่อกรองหา 0 หรือติดลบ
                filtered_df = df_stock[pd.to_numeric(df_stock['Stock'], errors='coerce') <= 0]
            else:
                filtered_df = df_stock
            
            # วนลูปแสดงผลรายการที่ผ่านการกรอง
            if not filtered_df.empty:
                for index, row in filtered_df.iterrows():
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                    with c1:
                        st.write(f"**{row['วัตถุดิบ']}**")
                        st.caption(f"หมวด: {row.get('Category', '-')} | ที่เก็บ: {row.get('storage_zone', '-')}")
                    with c2:
                        st.write(f"เหลือ: {row['Stock']} {row['Unit']}")
                    with c3:
                        stock_val = float(row['Stock']) if str(row['Stock']).replace('.','',1).isdigit() else 0
                        if stock_val > 0:
                            st.markdown("✅ **มีของ**")
                        else:
                            st.markdown("❌ **หมดแล้ว!**")
                    with c4:
                        item_id = str(row['ItemCode'])
                        if st.button("➕ เพิ่ม", key=f"add_mode_{item_id}"):
                            if item_id in st.session_state.shopping_cart:
                                st.session_state.shopping_cart[item_id] += 1
                            else:
                                st.session_state.shopping_cart[item_id] = 1
                            st.success(f"เพิ่ม {row['วัตถุดิบ']} แล้ว")
                    st.divider()
            else:
                if view_mode == "❌ เฉพาะรายการที่หมดแล้ว (Stock = 0)":
                    st.success("🎉 เยี่ยมมาก! ตอนนี้ไม่มีวัตถุดิบไหนหมดเลย ของในครัวยังครบถ้วนดีครับ")
                else:
                    st.info("ไม่มีข้อมูลสินค้า")
        else:
            st.info("ไม่มีข้อมูลสินค้า")

    with tab2:
        st.subheader("🛍️ รายการที่เลือกซื้อ (Shopping List)")
        
        if st.session_state.shopping_cart:
            total_price = 0
            for item_id, qty in list(st.session_state.shopping_cart.items()):
                item_row = df_stock[df_stock['ItemCode'].astype(str) == str(item_id)]
                if not item_row.empty:
                    name = item_row.iloc[0]['วัตถุดิบ']
                    price = float(item_row.iloc[0]['Price'])
                    unit = item_row.iloc[0]['Stock']
                    subtotal = price * qty
                    total_price += subtotal
                    
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    col1.write(f"**{name}**")
                    
                    # ปรับจำนวนในตะกร้า
                    new_qty = col2.number_input(f"จำนวน ({unit})", min_value=1, value=qty, key=f"qty_{item_id}")
                    st.session_state.shopping_cart[item_id] = new_qty
                    
                    col3.write(f"รวม: {price * new_qty:,.2f} ฿")
                    
                    if col4.button("🗑️", key=f"del_{item_id}"):
                        del st.session_state.shopping_cart[item_id]
                        st.rerun()
            
            st.markdown(f"### 💰 ยอดรวมทั้งหมด: **{total_price:,.2f} บาท**")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🧹 เคลียร์ตะกร้าทั้งหมด"):
                    st.session_state.shopping_cart.clear()
                    st.rerun()
            with col_b2:
                if st.button("✅ ยืนยันซื้อเสร็จสิ้น (เติมเข้าสต็อก)"):
                    for item_id, qty in st.session_state.shopping_cart.items():
                        idx = df_stock[df_stock['ItemCode'].astype(str) == str(item_id)].index
                        if not idx.empty:
                            current_qty = float(df_stock.loc[idx, 'Stock'].values[0])
                            df_stock.loc[idx, 'Stock'] = current_qty + float(qty)
                            
                    update_sheet_data(df_stock)
                    st.session_state.shopping_cart.clear()
                    st.success("อัปเดตสต็อกเข้าคลังเรียบร้อยแล้ว!")
                    st.rerun()
        else:
            st.info("ยังไม่มีสินค้าในตะกร้า")
# ==========================================
# 📦 หน้าอัพเดตสต็อกสินค้า
# ==========================================
elif menu == "📦 อัพเดตสต็อกสินค้า":
    st.title("📦 อัพเดตสต็อกสินค้า")
    st.write("แก้ไขจำนวนคงเหลือ ราคา หรือสถานที่จัดเก็บของวัตถุดิบ")
    
    if not df_stock.empty:
        selected_item = st.selectbox(
            "เลือกวัตถุดิบที่ต้องการแก้ไข:",
            df_stock['ItemCode'].astype(str) + " - " + df_stock['วัตถุดิบ']
        )
        
        if selected_item:
            item_id_val = selected_item.split(" - ")[0]
            item_row = df_stock[df_stock['ItemCode'].astype(str) == item_id_val].iloc[0]
            
            with st.form("update_form"):
                # ใช้ชื่อคอลัมน์ให้ตรงเป๊ะ ('Stock', 'Price', 'storage_zone', 'storage_slot')
                new_qty = st.number_input("จำนวนคงเหลือ (Stock)", value=float(item_row['Stock']) if pd.notna(item_row['Stock']) else 0.0, step=1.0)
                new_price = st.number_input("ราคาต่อหน่วย (Price)", value=float(item_row['Price']) if pd.notna(item_row['Price']) else 0.0, step=1.0)
                
                # แก้ชื่อตัวพิมพ์เล็ก-ใหญ่ให้ตรงกับหัวคอลัมน์จริง ('storage_zone')
                current_zone = str(item_row['storage_zone']) if 'storage_zone' in item_row and pd.notna(item_row['storage_zone']) else ""
                new_location = st.text_input("โซนเก็บของ (storage_zone)", value=current_zone)
                
                # เพิ่มช่องสำหรับกรอกช่องย่อย (storage_slot) ด้วย เพื่อไม่ให้ข้อมูลหาย
                current_slot = str(item_row['storage_slot']) if 'storage_slot' in item_row and pd.notna(item_row['storage_slot']) else ""
                new_slot = st.text_input("ช่องย่อย/ชั้น (storage_slot)", value=current_slot)
                
                submitted = st.form_submit_button("💾 บันทึกการเปลี่ยนแปลง")
                
                if submitted:
                    idx = df_stock[df_stock['ItemCode'].astype(str) == item_id_val].index
                    
                    # อัปเดตข้อมูลลงใน DataFrame ให้ครบทุกช่อง
                    df_stock.loc[idx, 'Stock'] = new_qty
                    df_stock.loc[idx, 'Price'] = new_price
                    df_stock.loc[idx, 'storage_zone'] = new_location
                    df_stock.loc[idx, 'storage_slot'] = new_slot
                    
              # เรียกใช้ฟังก์ชันอัปเดตข้อมูลกลับ Google Sheets
                    update_sheet_data(df_stock)
                    st.success("บันทึกข้อมูลลง Google Sheets สำเร็จ!")
                    st.rerun()
    else:
        st.warning("ไม่มีข้อมูลในระบบ")

 # --- 1. ฟังก์ชันโหลดข้อมูลสูตรอาหารแบบไม่ใช้ Cache ---


def load_recipes_data():
  try:
    recipe_df = pd.DataFrame(spreadsheet.worksheet('Recipe').get_all_records())
    ig_recipe_df = pd.DataFrame(
        spreadsheet.worksheet('IG_Recipe').get_all_records()
    )
    return recipe_df, ig_recipe_df
  except Exception as e:
    st.error(f'เกิดข้อผิดพลาดในการโหลดข้อมูลสูตรอาหาร: {e}')
    return pd.DataFrame(), pd.DataFrame() 

 # --- ฟังก์ชันตรวจสอบความพร้อมและคำนวณต้นทุนเมนูอาหาร ---
def check_and_cost_recipes(recipe_df, ig_recipe_df, stock_df):
  recipe_results = []

  if recipe_df.empty or ig_recipe_df.empty or stock_df.empty:
    return recipe_results

  for _, recipe in recipe_df.iterrows():
    r_id = recipe['Recipe_ID']
    r_name = recipe['Recipe_Name']
    r_group = recipe['Recipe_Group']

    # ดึงส่วนผสมของเมนูนี้
    ingredients = ig_recipe_df[ig_recipe_df['Recipe_ID'] == r_id]

    missing_items = []
    ready_to_cook = True
    total_recipe_cost = 0.0

    for _, ing in ingredients.iterrows():
      item_code = ing['Item_Code']
      item_name = ing['วัตถุดิบ']
      qty_need = float(ing['QTY_Need'] or 0)
      usage_unit = str(ing.get('Usage_Unit', ''))

      # ค้นหาข้อมูลสต็อกและราคาจากชีท IV (เทียบด้วย ItemCode)
      stock_row = stock_df[stock_df['ItemCode'] == item_code]

      if stock_row.empty:
        ready_to_cook = False
        missing_items.append({
            'Item_Code': item_code,
            'วัตถุดิบ': item_name,
            'Reason': 'ไม่พบรายการนี้ในสต็อก (IV)',
        })
        continue

      # ดึงค่าจากชีท IV อย่างปลอดภัย
      raw_stock = float(stock_row['Stock'].values[0] or 0)
      price_per_unit = float(stock_row['Price'].values[0] or 0)

      total_volume_per_unit = 1.0
      try:
        val = stock_row['Total_Volume_Per_Unit'].values[0]
        if val != '':
          total_volume_per_unit = float(val)
      except Exception:
        total_volume_per_unit = 1.0

      # แปลงสต็อกหน่วยใหญ่ให้เป็นหน่วยย่อย (เช่น ขวด -> มล.) ก่อนนำไปเช็ก
      total_available_in_base_unit = raw_stock * total_volume_per_unit

      # คำนวณต้นทุนต่อหน่วยย่อย
      cost_per_base_unit = (
          price_per_unit / total_volume_per_unit
          if total_volume_per_unit > 0
          else 0
      )
      ingredient_cost = qty_need * cost_per_base_unit
      total_recipe_cost += ingredient_cost

      # เช็กสต็อกว่าเพียงพอมั้ย (เทียบด้วยหน่วยย่อยที่แปลงแล้ว)
      if total_available_in_base_unit < qty_need:
        ready_to_cook = False
        missing_items.append({
            'Item_Code': item_code,
            'วัตถุดิบ': item_name,
            'Need': qty_need,
            'Current_Stock': total_available_in_base_unit,
            'Unit': usage_unit,
        })

    recipe_results.append({
        'Recipe_ID': r_id,
        'Recipe_Name': r_name,
        'Recipe_Group': r_group,
        'Ready': ready_to_cook,
        'Total_Cost': total_recipe_cost,
        'Missing_Items': missing_items,
    })

  return recipe_results 

st.markdown('---')
st.subheader('🍳 ระบบแนะนำเมนูอาหารและต้นทุนจากวัตถุดิบในตู้')

# 1. ปุ่มสำหรับกดโหลดหรือรีเฟรชข้อมูลสูตรอาหาร
if st.button('🔄 โหลด/อัปเดตข้อมูลเมนูอาหาร'):
  st.rerun()

