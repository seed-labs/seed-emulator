FROM iib_base_router
COPY bird.conf /etc/bird/bird.conf
COPY start.sh /
RUN chmod +x start.sh
CMD ["/start.sh"]
