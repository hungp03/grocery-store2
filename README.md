# Web bán hàng bách hóa

## Mô tả

**Grocery-store** là một ứng dụng **web** được thiết kế để **mô tả các chức năng cơ bản của 1 hệ thống thương mại điện tử**. Ứng dụng này tích hợp các thuật toán cơ bản để đề xuất sản phẩm dựa trên hành vi người dùng và nội dung của sản phẩm nhằm **cải thiện trải nghiệm người dùng ...**.

## Công nghệ sử dụng

- **Frontend**: React, Redux, Tailwind CSS
- **Backend**: Spring Boot, MySQL
- **Authentication**: JWT, Google Oauth
- **Recommendation**: Python, [Sentence-BERT](https://sbert.net/), [Annoy (Approximate Nearest Neighbors)](https://github.com/spotify/annoy), Cosine similarity

## Phân công công việc

| Thành viên    | Phân công                                                                                                     |
| ------------- | ------------------------------------------------------------------------------------------------------------- |
| Phạm Văn Hùng | Các tính năng liên quan đến giao diện chính, đăng nhập, đăng ký, thêm vào giỏ hàng... và tính năng thông minh |
| Vũ Gia Huy    | Các tính năng liên quan đến trang cá nhân người dùng, thanh toán, quản lý phản hồi người dùng                 |
| Hồ Anh Tuấn   | Các tính năng phần admin                                                                                      |

## Cài đặt và chạy dự án

1. Clone repo:

   ```bash
   git clone https://github.com/hungp03/grocery-store2
   cd grocery-store2

   ```

2. Cài đặt dependencies:

   ```bash
   # Frontend
   cd client
   npm install

   # Backend
   cd server
   # load các dependencies qua pom.xml

   # hệ thống đề xuất
   cd model
   # Tạo môi trường ảo
   python -m venv <tên môi trường>
   <tên môi trường>/Scripts/activate
   pip install -r requirements.txt
   ```

3. Cấu hình .env (Frontend & hệ thống đề xuất) và application.yml (Backend) trên môi trường development
   Các tham số .env (Frontend):

   - VITE_BACKEND_URL(url api backend)
   - VITE_BACKEND_TARGET(url gốc của backend)
   - VITE_GOOGLE_CLIENT_ID(token sử dụng đăng nhập google từ google console)

   Các tham số .env cho hệ thống đề xuất:

   - DB_URL(kết nối sql qua SQLAchemy)
   - SERVER(url gốc của backend)
   - REDIS_URL(kết nối redis)

4. Chạy ứng dụng
   - Chạy frontend ở chế độ production:
   ```bash
   cd client
   npm run build
   npm run preview
   ```
   - Chạy mô hình đề xuất
   ```bash
   cd model
   uvicorn main:app
   ```
   - Note: tải file jar (Backend) ở phần dưới để không cần phải cấu hình application.yml thủ công

Database & Backend(Jar) và các file liên quan: [Tại đây](https://drive.google.com/drive/folders/1BLnMsHC76ukZnPv20yTgdImvKblKMb5v?usp=drive_link)
