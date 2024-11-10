# Web bán hàng bách hóa

## Mô tả
**Grocery-store** là một ứng dụng **web** được thiết kế để **mô tả các chức năng cơ bản của 1 hệ thống thương mại điện tử**. Ứng dụng này tích hợp các thuật toán cơ bản để đề xuất sản phẩm dựa trên hành vi người dùng và nội dung của sản phẩm nhằm **cải thiện trải nghiệm người dùng ...**.

## Công nghệ sử dụng
- **Frontend**: React, Redux, Tailwind CSS
- **Backend**: Spring Boot, MySQL
- **Authentication**: JWT, Google Oauth
- **Intelligent System**: Python, [Sentence-BERT](https://sbert.net/), [Annoy (Approximate Nearest Neighbors)](https://github.com/spotify/annoy), Cosine similarity

## Cài đặt và chạy dự án
1. Clone repo:
   ```bash
   git clone https://github.com/hungp03/grocery-store
   cd grocery-store

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
3. Cấu hình .env (Frontend & hệ thống đề xuất) và application.yml (Backend)
4. Chạy ứng dụng

Database: [Here](https://drive.google.com/drive/folders/1BLnMsHC76ukZnPv20yTgdImvKblKMb5v?usp=drive_link)

