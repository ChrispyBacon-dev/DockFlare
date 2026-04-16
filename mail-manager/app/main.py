from waitress import serve
from app import create_app

if __name__ == '__main__':
    app = create_app()
    serve(app, host='0.0.0.0', port=8025)
