# Website lời chúc 20/10 — deploy lên Render

## Đăng công khai bằng Render + GitHub

1. Giải nén ZIP này; mở thư mục `20_10_Render_Package`.
2. Tạo một repository mới trên GitHub, ví dụ `loi-chuc-2010`. Có thể để Public để Render dễ kết nối. Tạo repository trống, không thêm README từ GitHub.
3. Trong repo mới chọn **Add file → Upload files**. Kéo các tệp và thư mục bên trong `20_10_Render_Package` vào vùng upload, sao cho `app.py`, `requirements.txt`, `templates/` và `static/` nằm ngay ở gốc repo. Nhấn **Commit changes**.
4. Đăng nhập Render: https://dashboard.render.com/
5. Chọn **New + → Web Service** và kết nối tài khoản GitHub nếu được hỏi.
6. Chọn repo `loi-chuc-2010` rồi bấm **Connect**.
7. Điền cấu hình:
   - **Name:** `loi-chuc-2010` (hoặc tên chưa được người khác dùng)
   - **Language/Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
   - **Instance Type:** Free (nếu được cung cấp)
8. Bấm **Create Web Service** và đợi phần Events/Logs báo deploy thành công.
9. Mở URL `https://<tên-dịch-vụ>.onrender.com` hiện trên trang dịch vụ. Gửi đường link đó cho mọi người; họ không cần cùng Wi-Fi với máy của bạn.

## Ghi chú

- Ứng dụng tự lắng nghe ở `0.0.0.0` và đọc cổng từ biến môi trường `PORT`, như Render yêu cầu.
- Render Free có thể đưa dịch vụ vào trạng thái ngủ sau một thời gian không có truy cập; lần mở tiếp theo có thể cần chờ khởi động.
- Cơ sở dữ liệu hiện là SQLite trong thư mục `instance`. Ổ đĩa mặc định của Render là tạm thời, nên dữ liệu người ghé thăm/lời chúc không được đảm bảo còn sau khi service khởi động lại hoặc deploy lại. Gói này ưu tiên cách triển khai dễ nhất; nếu cần giữ dữ liệu lâu dài, hãy cấu hình cơ sở dữ liệu bền vững riêng trước khi dùng rộng rãi.
- Không commit cơ sở dữ liệu cá nhân, thông tin bí mật, hay service-account keys lên GitHub.
