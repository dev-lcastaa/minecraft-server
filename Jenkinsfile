pipeline {
    agent { label 'production' }

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    parameters {
        booleanParam(
            name: 'ACCEPT_EULA',
            defaultValue: true,
            description: 'Accept https://aka.ms/MinecraftEULA before starting the server.'
        )
        string(
            name: 'FORGE_VERSION',
            defaultValue: 'recommended',
            description: 'Forge version for Minecraft 1.20.1; match your clients/modpack.'
        )
        string(
            name: 'RCON_BIND_IP',
            defaultValue: '192.168.1.208',
            description: 'Production host LAN/VPN IPv4 address for RCON; do not use 0.0.0.0.'
        )
    }

    environment {
        EULA = "${params.ACCEPT_EULA}"
        FORGE_VERSION = "${params.FORGE_VERSION}"
        RCON_BIND_IP = "${params.RCON_BIND_IP}"
        RCON_PASSWORD = credentials('minecraft-rcon-password')
        MINECRAFT_IMAGE = "minecraft-forge:build-${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Validate') {
            steps {
                sh '''
                    set -eu
                    if [ "$EULA" != "true" ]; then
                        echo "Enable ACCEPT_EULA after reviewing the Minecraft EULA." >&2
                        exit 1
                    fi
                    if [ ! -d mods ]; then
                        echo "Add the mods directory to the build workspace before building." >&2
                        exit 1
                    fi
                    case "$RCON_PASSWORD" in
                        *[!A-Za-z0-9_-]*)
                            echo "RCON password must use only letters, digits, underscore, and hyphen." >&2
                            exit 1
                            ;;
                    esac
                    if [ "${#RCON_PASSWORD}" -lt 24 ]; then
                        echo "RCON password must contain at least 24 characters." >&2
                        exit 1
                    fi
                    if [ -z "$RCON_BIND_IP" ] || [ "$RCON_BIND_IP" = "0.0.0.0" ]; then
                        echo "Set RCON_BIND_IP to the production host's LAN/VPN IPv4 address." >&2
                        exit 1
                    fi
                    docker version
                    docker compose version
                    docker compose config --quiet
                '''
            }
        }

        stage('Build') {
            steps {
                sh 'docker compose build --pull'
            }
        }

        stage('Deploy') {
            steps {
                sh 'docker compose up -d --no-build --wait --wait-timeout 900'
                sh 'docker compose ps'
            }
            post {
                failure {
                    sh 'docker compose logs --no-color --tail 200 minecraft'
                }
            }
        }
    }
}
