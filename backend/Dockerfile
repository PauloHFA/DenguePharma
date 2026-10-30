# Multi-stage build para o backend Spring Boot DenguePharma
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /workspace

# Instala ferramentas de build
RUN apk add --no-cache maven

# Copia dependências e fontes
COPY pom.xml .
COPY src ./src

# Compila o JAR do backend pulando testes no container build
RUN mvn clean package -DskipTests

# Estágio de execução enxuto
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

COPY --from=builder /workspace/target/denguepharma-backend-*.jar app.jar

EXPOSE 18080

ENTRYPOINT ["java", "-Djava.security.egd=file:/dev/./urandom", "-jar", "app.jar"]
