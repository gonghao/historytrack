# HistoryTrack

This is an easy python project with Flask.

## API

### 网页代理访问地址

使用网页代理访问的形式可以记录页面的访问信息

URI: /link/{dest_url}

Method: Get

Parameter:

*  dest_url: 需要访问的页面完整 URI, 并对 URI 进行编码

例如:

代理访问 http://ghsky.com

则需要生成链接：/link/http%253A%252F%252Fghsky.com

## Misc

对于首页的定制，没有通过程序进行，而是在模板里面直接写死了，当然也可以利用程序为不同用户生成不同的首页，但是暂没提供此功能
