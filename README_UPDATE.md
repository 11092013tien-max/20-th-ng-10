# Bản cập nhật nhạc dịu dàng + hiệu ứng mượt

Gói này chỉ chứa hai tệp cần cập nhật trong repository GitHub đang dùng:

- `templates/index.html`
- `static/20_10_magic_theme.mp3`

## Cách cập nhật trên GitHub

1. Mở repository đang kết nối với Render.
2. Mở thư mục `templates`, chọn `Add file` → `Upload files`, tải `index.html` từ thư mục `templates` trong gói này lên, rồi `Commit changes`.
3. Mở thư mục `static`, chọn `Add file` → `Upload files`, tải `20_10_magic_theme.mp3` từ thư mục `static` trong gói này lên, rồi `Commit changes`.
4. Chờ Render tự deploy (hoặc vào Manual Deploy → Deploy latest commit).
5. Mở website và tải mới mạnh bằng Ctrl+F5 trên máy tính. Trên điện thoại, đóng tab rồi mở lại hoặc làm mới trang.

## Những thay đổi

- Thay bản nhạc nền cũ bằng một giai điệu instrumental tự tổng hợp, vui dịu, tông trưởng, có tiếng piano/chuông nhẹ; nhạc bắt đầu khi chạm mở cổng để tương thích chính sách âm thanh trên điện thoại.
- Giảm hạt nền, giới hạn vòng lặp vẽ khoảng 40 fps và giảm các hiệu ứng shadow/filter nặng.
- Chuyển cảnh cổng -> khu vườn khoảng 2.5–3.5 giây thay vì chờ lâu; vẫn giữ vòng sáng, hạt lấp lánh và cánh hoa.
- Đổi hiệu ứng Morph khi hiện thiệp sang fade/scale mượt nhẹ hơn để tránh khựng trên điện thoại.

Nếu Render dùng cache cũ cho âm thanh, mở trực tiếp `/static/20_10_magic_theme.mp3` ở website để kiểm tra tệp đã được cập nhật và làm mới trang.
