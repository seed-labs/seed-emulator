<?php
/*
 * SEED邮件系统 Roundcube配置
 */

$config = array();

// 数据库配置
$config['db_dsnw'] = 'sqlite:////var/roundcube/db/sqlite.db?mode=0646';

// IMAP配置
$config['default_host'] = array(
    'ssl://localhost' => 'SEED邮件系统 (本地)',
    'ssl://mail.seedemail.net' => 'SeedEmail.net',
    'ssl://mail.corporate.local' => 'Corporate Local', 
    'ssl://mail.smallbiz.org' => 'Small Business'
);

$config['default_port'] = 993;
$config['imap_conn_options'] = array(
    'ssl' => array(
        'verify_peer' => false,
        'verify_peer_name' => false,
        'allow_self_signed' => true
    )
);

// SMTP配置
$config['smtp_server'] = 'tls://localhost';
$config['smtp_port'] = 587;
$config['smtp_user'] = '%u';
$config['smtp_pass'] = '%p';

$config['smtp_conn_options'] = array(
    'ssl' => array(
        'verify_peer' => false,
        'verify_peer_name' => false,
        'allow_self_signed' => true
    )
);

// 界面配置
$config['skin'] = 'elastic';
$config['language'] = 'zh_CN';
$config['date_format'] = 'Y-m-d';
$config['time_format'] = 'H:i';

// 功能配置
$config['enable_installer'] = false;
$config['auto_create_user'] = true;
$config['check_all_folders'] = true;

// 插件
$config['plugins'] = array(
    'archive',
    'zipdownload',
    'managesieve'
);

// 上传限制
$config['max_message_size'] = '5M';

// 日志
$config['log_driver'] = 'stdout';
$config['log_level'] = RCUBE_LOG_WARNING;

// 安全
$config['force_https'] = false;
$config['use_https'] = false;
$config['login_autocomplete'] = 2;

// 会话
$config['session_lifetime'] = 60; // 60分钟

return $config;
?>