<?php

/**
 * Roundcube Webmail 配置文件
 * 用于 SEED 邮件系统 (29-email-system)
 * 
 * 支持三个邮件域：
 * - seedemail.net
 * - corporate.local
 * - smallbiz.org
 */

/* 本地配置 */
$config = array();

// ----------------------------------
// 数据库配置
// ----------------------------------
$config['db_dsnw'] = 'mysql://roundcube:roundcube_pass@roundcube-db/roundcubemail';

// ----------------------------------
// IMAP 配置
// ----------------------------------
// IMAP主机配置
$config['imap_host'] = array(
    'mail-150-seedemail:143',
    'mail-151-corporate:143',
    'mail-152-smallbiz:143',
);
$config['imap_host_labels'] = array(
    'SeedEmail.net (Public Email)',
    'Corporate Mail (Enterprise)',
    'SmallBiz.org (Small Business)',
);
$config['default_host'] = 'mail-150-seedemail';

// IMAP 连接选项
$config['imap_auth_type'] = null;  // 自动检测
$config['imap_delimiter'] = null;  // 自动检测
$config['imap_disabled_caps'] = array(); // 不禁用任何功能
$config['imap_timeout'] = 0;  // 使用默认超时
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
// 根据用户的邮箱域名自动选择SMTP服务器
$config['smtp_server'] = '%h';  // 使用与IMAP相同的主机
$config['smtp_port'] = 25;
$config['smtp_user'] = '%u';    // 使用IMAP用户名
$config['smtp_pass'] = '%p';    // 使用IMAP密码
$config['smtp_auth_type'] = '';  // 默认验证方式
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
$config['support_url'] = 'http://localhost:5000';  // 指向webmail管理界面
$config['product_name'] = 'SEED Webmail';
$config['des_key'] = 'rcmail-!24ByteDESkey*Str';  // 24字节的DES密钥

// 语言和本地化
$config['language'] = 'zh_CN';  // 默认中文
$config['username_domain'] = '';  // 不自动添加域名

// 界面配置
$config['skin'] = 'elastic';  // 使用现代化主题
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
$config['draft_autosave'] = 300;  // 每5分钟自动保存草稿
$config['mime_param_folding'] = 1;
$config['identities_level'] = 0;  // 允许用户编辑身份

// 显示设置
$config['preview_pane'] = true;
$config['preview_pane_mark_read'] = 0;  // 不自动标记为已读
$config['mail_pagesize'] = 50;  // 每页显示50封邮件
$config['addressbook_pagesize'] = 50;

// 邮件撰写
$config['compose_responses_static'] = false;
$config['reply_mode'] = 0;  // 在邮件下方回复
$config['forward_attachment'] = false;

// ----------------------------------
// 安全设置
// ----------------------------------
$config['force_https'] = false;  // 实验环境不强制HTTPS
$config['use_https'] = false;
$config['login_autocomplete'] = 2;  // 允许浏览器自动填充
$config['password_charset'] = 'UTF-8';

// 会话配置
$config['session_lifetime'] = 30;  // 会话30分钟
$config['session_samesite'] = 'Lax';
$config['ip_check'] = false;  // 不检查IP变化（实验环境）

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
$config['enable_installer'] = false;  // 禁用安装程序
$config['dont_override'] = array();
$config['enable_spellcheck'] = false;  // 禁用拼写检查（需要额外配置）

?>
