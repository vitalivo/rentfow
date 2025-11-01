FROM nginx:alpine

# Копируем простой HTML (заглушка)
COPY index.html /usr/share/nginx/html/index.html

# Открываем порт
EXPOSE 80

# Запускаем nginx
CMD ["nginx", "-g", "daemon off;"]