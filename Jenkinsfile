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
        
        stage('Build Docker Image') {
            steps {
                script {
                    // Build the Docker image
                    sh "docker build -t ${DOCKER_IMAGE} ."
                }
            }
        }

        stage('Deploy to Docker') {
            steps {
                script {
                    // Bring down existing containers if necessary
                    sh "docker-compose down"

                    // Create .env file dynamically
                    writeFile file: '.env', text: """
                    BOT_TOKEN=${BOT_TOKEN}
                    POSTGRES_DB=${POSTGRES_DB}
                    POSTGRES_USER=${POSTGRES_USER}
                    POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
                    CONNECTION_STRING=Host=db;Database=${env.POSTGRES_DB};Username=${env.POSTGRES_USER};Password=${env.POSTGRES_PASSWORD};Port=5432;
                    """

                    // Run Docker Compose
                    sh "docker-compose up -d --build"
                }
            }
        }

    }
    post {
        success {
            echo 'Pipeline execution completed successfully!'
        }
        failure {
            echo 'Pipeline failed. Attempting to clean up resources...'
        }
    }
}