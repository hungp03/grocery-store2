# Grocery Store Web Application

## Description

**Grocery-store** is a **web application** designed to **demonstrate the basic functionalities of an e-commerce system**. 
This application integrates basic algorithms to recommend products based on user behavior and product content, aiming to **enhance the user experience...**.

## Technologies Used

- **Frontend**: React, Redux, Tailwind CSS
- **Backend**: Spring Boot, MySQL
- **Authentication**: JWT, Google OAuth
- **Recommendation System**: Python, [Sentence-BERT](https://sbert.net/), [Annoy (Approximate Nearest Neighbors)](https://github.com/spotify/annoy), Cosine similarity

## Task Assignments

| Member         | Responsibilities                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------- |
| Phạm Văn Hùng | Main interface features, login, registration, cart... and intelligent features                   |
| Vũ Gia Huy     | User profile page, order, payment features, user feedback management                                          |
| Hồ Anh Tuấn    | Admin panel features                                                                                   |

## Installation and Running the Project

1. Clone the repository:

   ```bash
   git clone https://github.com/hungp03/grocery-store2
   cd grocery-store2
   ```

2. Install dependencies:

   ```bash
   # Frontend
   cd client
   npm install

   # Backend
   cd server
   # Load dependencies via pom.xml

   # Recommendation system
   cd model
   # Create a virtual environment
   python -m venv <environment_name>
   <environment_name>/Scripts/activate
   pip install -r requirements.txt
   ```

3. Configure `.env` (Frontend & Recommendation System) and `application.yml` (Backend) for the development environment.

   **Frontend `.env` parameters:**

   - `VITE_BACKEND_URL` (Backend API URL)
   - `VITE_BACKEND_TARGET` (Backend base URL)
   - `VITE_GOOGLE_CLIENT_ID` (Google Console token for Google login)

   **Recommendation System `.env` parameters:**

   - `DB_URL` (SQL connection via SQLAlchemy)
   - `SERVER` (Backend base URL)
   - `REDIS_URL` (Redis connection)

4. Run the application:
   - Run the **Frontend** in production mode:
     ```bash
     cd client
     npm run build
     npm run preview
     ```
   - Run the **Recommendation System**:
     ```bash
     cd model
     uvicorn main:app
     ```
   - Download the backend `.jar` file (see the link below) to avoid manual configuration of `application.yml`.

   Database, Backend (Jar), and related files: [Download Here](https://drive.google.com/drive/folders/1BLnMsHC76ukZnPv20yTgdImvKblKMb5v?usp=drive_link)

## Contributors

Thanks to the following people for contributing to this project:

<table>
    <tr>
        <td align="center">
            <a href="https://github.com/hungp03">
                <img 
                    src="https://avatars.githubusercontent.com/u/118011821?v=4"
                    alt="hungp03" width="100px;" height="100px;" 
                    style="border-radius: 4px; background: #fff;"
                /><br />
                <sub><b>hungp03</b></sub>
            </a>
        </td>
        <td align="center">
            <a href="https://github.com/TuanHHH">
                <img 
                    src="https://avatars.githubusercontent.com/u/112617035?v=4"
                    alt="TuanHHH" width="100px;" height="100px;"                 
                    style="border-radius: 4px; background: #fff;"
                /><br />
                <sub><b>TuanHHH</b></sub>
            </a>
        </td>
        <td align="center">
            <a href="https://github.com/HuyLearnProgram">
                <img 
                    src="https://avatars.githubusercontent.com/u/99035341?v=4"
                    alt="HuyLearnProgram" width="100px;" height="100px;"
                    style="border-radius: 4px; background: #fff;"
                /><br />
                <sub><b>HuyLearnProgram</b></sub>
            </a>
        </td>
    </tr>
</table>

