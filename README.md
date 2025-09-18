# StudyPulse Backend

Django REST API backend for the StudyPulse Learning Platform.

## Setup
1. Create virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`

4. Run migrations:
```bash
python manage.py migrate
```

5. Start development server:
```bash
python manage.py runserver
```
