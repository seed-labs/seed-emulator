<?php
  $config['db_dsnw'] = 'sqlite:////var/roundcube/db/sqlite.db?mode=0646';
  $config['db_dsnr'] = '';
  $config['imap_host'] = 'ssl://mail.seedemail.net:993';
  $config['smtp_host'] = 'tls://mail.seedemail.net:587';
  $config['username_domain'] = '';
  $config['temp_dir'] = '/tmp/roundcube-temp';
  $config['skin'] = 'elastic';
  $config['request_path'] = '/';
  $config['plugins'] = array_filter(array_unique(array_merge($config['plugins'], ['archive', 'zipdownload', 'managesieve'])));
  
