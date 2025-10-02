<?php

/**
 * Roundcube Webmail 配置文件
 * 用于 SEED 邮件系统 (29-1-email-system) - 真实版
 * 
 * 支持六个邮件服务商：
 * - QQ邮箱 (qq.com)
 * - 163邮箱 (163.com)
 * - Gmail (gmail.com)
 * - Outlook (outlook.com)
 * - 企业邮箱 (company.cn)
 * - 自建邮箱 (startup.net)
 */

/* 本地配置 */
$config = array();

// ----------------------------------
// 数据库配置
// ----------------------------------
$config['db_dsnw'] = 'mysql://roundcube:roundcube_pass@roundcube-db/roundcubemail';

// ----------------------------------
// IMAP 配置 - 支持多个真实邮件服务商
// ----------------------------------
$config['imap_host'] = array(
    'mail-qq-tencent:143',
    'mail-163-netease:143',
    'mail-gmail-google:143',
    'mail-outlook-microsoft:143',
    'mail-company-aliyun:143',
    'mail-startup-selfhosted:143',
);
$config['imap_host_labels'] = array(
    'QQ邮箱 (qq.com)',
    '163邮箱 (163.com)',
    'Gmail (gmail.com)',
    'Outlook (outlook.com)',
    '企业邮箱 (company.cn)',
    '自建邮箱 (startup.net)',
);
$config['default_host'] = 'mail-qq-tencent';

// IMAP 连接选项
$config['imap_auth_type'] = null;
$config['imap_delimiter'] = null;
$config['imap_disabled_caps'] = array();
$config['imap_timeout'] = 0;
$config['imap_conn_options'] = array(
    'ssl' => array(
        'verify_peer'       => false,
        'verify_peer_name'  => false,
        'allow_self_signed' => true,
    ),
);

// ----------------------------------
// SMTP 配置
// ----------------------------------
$config['smtp_server'] = '%h';  // 使用与IMAP相同的主机
$config['smtp_port'] = 25;
$config['smtp_user'] = '%u';
$config['smtp_pass'] = '%p';
$config['smtp_auth_type'] = '';
$config['smtp_conn_options'] = array(
    'ssl' => array(
        'verify_peer'       => false,
        'verify_peer_name'  => false,
        'allow_self_signed' => true,
    ),
);

// ----------------------------------
// 系统配置
// ----------------------------------
$config['support_url'] = 'http://localhost:5001';
$config['product_name'] = 'SEED Webmail - 真实版';
$config['des_key'] = 'rcmail-!24ByteDESkey*Str';

// 语言和本地化
$config['language'] = 'zh_CN';
$config['username_domain'] = '';

// 界面配置
$config['skin'] = 'elastic';
$config['timezone'] = 'Asia/Shanghai';
$config['date_format'] = 'Y-m-d';
$config['time_format'] = 'H:i';

// ----------------------------------
// 插件配置
// ----------------------------------
$config['plugins'] = array(
    'archive',
    'zipdownload',
    'managesieve',
);

// ----------------------------------
// 邮件设置
// ----------------------------------
$config['draft_autosave'] = 300;
$config['mime_param_folding'] = 1;
$config['identities_level'] = 0;

// 显示设置
$config['preview_pane'] = true;
$config['preview_pane_mark_read'] = 0;
$config['mail_pagesize'] = 50;
$config['addressbook_pagesize'] = 50;

// 邮件撰写
$config['compose_responses_static'] = false;
$config['reply_mode'] = 0;
$config['forward_attachment'] = false;

// ----------------------------------
// 安全设置
// ----------------------------------
$config['force_https'] = false;
$config['use_https'] = false;
$config['login_autocomplete'] = 2;
$config['password_charset'] = 'UTF-8';

// 会话配置
$config['session_lifetime'] = 30;
$config['session_samesite'] = 'Lax';
$config['ip_check'] = false;

// ----------------------------------
// 日志配置
// ----------------------------------
$config['log_driver'] = 'file';
$config['log_date_format'] = 'Y-m-d H:i:s O';
$config['smtp_log'] = true;
$config['log_logins'] = true;
$config['log_session'] = false;
$config['sql_debug'] = false;
$config['imap_debug'] = false;
$config['smtp_debug'] = false;

// ----------------------------------
// 其他配置
// ----------------------------------
$config['enable_installer'] = false;
$config['dont_override'] = array();
$config['enable_spellcheck'] = false;

?>


