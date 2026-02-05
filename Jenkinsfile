pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "telegram-bot-scraper:latest"

        BOT_TOKEN = credentials('telegram-bot-token')
        POSTGRES_DB = credentials('database-name-staging')
        POSTGRES_USER = credentials('database-user-staging')
        POSTGRES_PASSWORD = credentials('postgres-password-staging')
    }

    stages {
        stage('Deploy with Docker Compose') {
            steps {
                script {
                    // Create .env dynamically
                    writeFile file: '.env', text: """
BOT_TOKEN=${BOT_TOKEN}
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
"""

                    sh """
                        docker-compose down || true
                        docker-compose up -d --build
                    """
                }
            }
        }
    }

    post {
        success {
            echo '✅ Pipeline completed successfully'
        }
        failure {
            echo '❌ Pipeline failed'
        }
    }
}
