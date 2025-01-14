# 对于挂载阿里云盘的播放器，实现自动更新视频，并重命名为原产国名称以及季度剧集的自动计算
# 原产国名称来源于TMDb
# 可以使用crontab指令使其按需求完成自动化，并根据需求选择是否记入日志
# 关联聚合云推api，实现剧集自动更新到库后的微信推送通知
# 目前仅支持单一视频格式，即.mp4 or .mkv，暂未适配字幕文件
# 需要用户自己维护一个txt文件，作为自动更新的数据来源
# txt格式为“剧名S1#url” ---> (eg.  为美好的世界献上祝福S3#https://自己去找url.com)
# txt文件中剧名和阿里云盘存储的目录名相一致
# Updated on April 23     ----by wsubset
# 仅供学习交流，请勿商用，若有不妥之处，侵联必删



from aligo import Aligo,EMailConfig
from themoviedb import TMDb
from pathlib import Path
import json
import re
import requests
import time
import logging


# 读取txt文件，返回name_url_dict
# txt格式为“剧名S1#url” ---> (eg.  为美好的世界献上祝福S3#https://自己去找url.com)
# 请注意将txt中剧名和阿里云盘存储的目录名相一致
# 建立name_url_dict字典用于快速查找剧名对应的url
def creat_dict():
    with open("*****你的txt文件在本地的地址*****", "r") as file: # 此处填写你自己的txt文件路径
        lines = file.readlines()

    # 创建空字典来存储键值对
    name_url_dict = {}

    # 遍历每一行数据
    for line in lines:
        # 去除每行两端的空白符（如换行符）
        line = line.strip()

        # 根据分隔符分割键值对
        name, url = line.split("#")

        # 添加到字典中（去除空格）
        name_url_dict[name.strip()] = url.strip()

    return name_url_dict

# 用递归调用深度优先遍历目录，找到文件路径
def local_tree(name,parent_file_id):
    file_list = ali.get_file_list(parent_file_id)
    for file in file_list:
        if file.name == name:
            path_1 = '/' + file.name
            return path_1
        elif file.type == 'folder':
            #print(file.name)
            path = local_tree(name,file.file_id)
            if path is not None:
                path = file.name + path
                return path
    return None

# 调用local_tree，返回绝对路径
def find_path(file_name):
    file = ali.get_folder_by_path('file_1/file_2') # 填写你希望开始路径，减少查找路径时间
    path_sub = local_tree(file_name,file.file_id)
    if path_sub is not None:
        path = 'file_1/file_2' + path_sub # 此处与上方同时修改
        return path
    else:
        print("----------未找到相关文件夹----------")

# 用于找到可用来查找的剧名及季度，减少一个季度输入
def tool(path):
    full_name = path.split('/')[-1]
    name = full_name.split('S')[0]
    ss = full_name.split('S')[1]
    return name,ss

# share相关函数，最终得到share_token
def to_file():
    Path('aliyun.json5').write_text(
        json.dumps([f.to_dict() for f in all_files], ensure_ascii=False),
        encoding='utf8'
    )

def tree_share(share_token, parent_file_id):
    file_list = ali.get_share_file_list(share_token, parent_file_id=parent_file_id)
    for file in file_list:
        #        print(file.name)
        if file.type == 'folder':
            continue
        all_files.append(file)


#            tree_share(share_token, file.file_id)

def share_main(search_url):
    share_msg = search_url
    share_id = ali.share_link_extract_code(share_msg).share_id
    share_parent_id = share_msg.split('/')[-1]
    # print(share_parent_id)
    # print (share_id)
    share_token = ali.get_share_token(share_id)
    tree_share(share_token, share_parent_id)
    to_file()
    return share_token

# file_list 排序函数，可以用注释中的优化，但是后面调用了，此处就不修改了
def file_sort(file_list):
    # 可查看未排序前的 id-name 映射
    # file_list
    # 新增一个int list并与原list排序相同
    j = 0
    num_list = []
    for file in file_list:
        num = ''.join(re.findall(r'\d',file_list[j].name))
        num_list.append(num)
        j += 1
    # 合并并排序两条list
    folder_list = list(zip(num_list,file_list))
    folder_list = sorted(folder_list,key = (lambda x:x[0]))
    # 合并后切片保留id-name
    folder_list_2 = [row[1] for row in folder_list]

# Updated on April 19th      和过去狠狠切割
#    folder_list_2 = file_list.sort(key=lambda x:x.name)
    return folder_list_2

# 用两个文件夹内容长度对比，返回两个长度（若修改file_sort函数，此处len()也请修改
def collision(file_local,all_files_sorted):
#    all_files_sorted = file_sort(all_files)
#    for item in all_files_sorted:
#        print(item.name)

    # 计算file_local长度
    file_local_list = ali.get_file_list(file_local.file_id)
    length_file = 0
    for file in file_local_list:
        length_file += 1
#    print(length_file)
    # length_share长度
    length_share = len(all_files_sorted)
#    print(length_share)
    return length_file,length_share

def creat_name(name,all_files_sorted,length_file,length_share,ss):
    new_name_list = []
    tv_oname = None #带出局部变量
    tmdb = TMDb(key="YOUR API KEY", language="zh-CN", region="CN")  #在此处修改为自己的api，可根据需求修改语言地区参数
    results = tmdb.search().multi(name)
    for result in results:
        if result.is_tv():
            tv = tmdb.tv(result.id).details()
            tv_oname = tv.original_name
#            print(tv, tv.original_name)
        else:
            continue
    if tv_oname is None:
        print("----------未查询到该剧集----------")
    count = length_share - length_file
    i = 0
    #ss = input('输入季度<=2位：')
    while i < count:
        ra_str = re.split('\.',all_files_sorted[length_file].name)
        suffix = ra_str[-1]
        new_name = tv_oname + ' S' + str(ss).rjust(2,'0') + 'E' + str(length_file + 1).rjust(2,'0') + '.' + suffix
        new_name_list.append(new_name)
        length_file += 1
        i += 1
    return new_name_list

def save(file_local,all_files_sorted,share_token,length_file,length_share,ss,name):
    new_name = creat_name(name,all_files_sorted,length_file,length_share,ss)
    i = 0
    count = length_share - length_file
    while i < count:
        ali.share_file_saveto_drive(all_files_sorted[length_file].file_id,share_token,
                                    file_local.file_id,new_name = new_name[i])
#           print(new_name[i])
        length_file += 1
        print('----------{}已更新----------'.format(new_name[i]))
        i += 1
    return length_share


# 监测URL是否正常响应
def url_check(url):
    # 当前时间
    check_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print("开始监测：%s -- %s" % (url, check_time))

    try:
        # 请求URL， 设置3s超时
        r = requests.get(url, timeout=3)
        if r.status_code != 200:
            # 请求响应状态异常
            msg = "监控的URL：%s%sHttp状态异常：%s%s监测时间：%s" % (url, "\n\n", r.status_code, "\n\n", check_time)
            print("监测结果：异常（Http状态异常:%s） -- %s" % (r.status_code, check_time))
            # 通过云推推送消息
            yuntui_push(msg)

        else:
            # 请求响应正常
            print("监测结果：正常 -- %s" % check_time)


    except requests.exceptions.ConnectTimeout:
        # 请求响应超时
        msg = "监控的URL：%s%s请求异常：%s%s监测时间：%s" % (url, "\n\n", "请求超时", "\n\n", check_time)
        print("监测结果：超时 -- %s" % check_time)
        # 通过云推推送消息
        yuntui_push(msg)


# 将预警消息通过云推推送
def yuntui_push(content):
    # 当前时间
    push_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # 云推接口的信息配置，可以通过 https://tui.juhe.cn 自行注册创建
    # 可以配置邮件、钉钉机器人、微信公众号等接收方式
    # 根据需要进行修改
    token = "YOUR TOKEN"
    service_id = "YOUR SERVICE ID"
    title = "title"
    doc_type = "markdown"
    body = {"token": token, "service_id": service_id, "title": title, "content": content, "doc_type": doc_type}
    try:
        r = requests.post("https://tui.juhe.cn/api/plus/pushApi", data=body, timeout=15)
        push_res = json.loads(r.content)

        code = push_res['code']
        if code == 200:
            print("推送结果：成功 -- %s" % push_time)
        else:
            print("推送结果：失败（%s） -- %s" % (push_res['reason'], push_time))
    except requests.exceptions.ConnectTimeout:
        print("推送结果：超时 -- %s" % push_time)


if __name__ == '__main__':
    # 只记录WARNING及以上的日志，减少日志
    logging.basicConfig(level=logging.WARNING)

    # 使用邮件方式进行登陆，若登陆过期可以收到二维码邮件，更便于自动化
    #ali = Aligo()  # 第一次使用会弹出二维码，可扫码登陆
    email_config = EMailConfig(
        email='你接收邮件的邮箱',
        # 自配邮箱
        user='发送邮件的邮箱',
        password='该邮箱的password',
        host='按需要填',
        port=0,
    )
    ali = Aligo(email=email_config)
    user = ali.get_user()  # 获取用户信息
    name_url_dict = {}
    name_url_dict = creat_dict()

    # 用字典按行进行自动化
    #    full_name = '防风少年S1'
    for full_name in name_url_dict:
        #        print(full_name)

        # 下面进行数据初始化
        all_files = []

        # 用full_name 深度优先遍历找到绝对路径
        path = find_path(full_name)

        # 按path找到file_local，计算其长度
        file_local = ali.get_folder_by_path(path)
        if file_local is None:
            raise RuntimeError('指定的文件夹不存在')
        print('----------获取信息完成----------')

        [name, ss] = tool(path)
        search_url = name_url_dict[full_name]
        # 检测url是否联通
        url_check(search_url)
        share_token = share_main(search_url)
        print('----------获取共享文档完成----------')
        all_files_sorted = file_sort(all_files)
        [length_file, length_share] = collision(file_local, all_files_sorted)
        # print(length_file,length_share)
        if length_file == length_share:
            print("----------{} 暂未更新----------".format(name))
            time.sleep(10) # 可自定义时长，建议保留防止过多请求导致连接中断
        else:
            ep = save(file_local, all_files_sorted, share_token, length_file, length_share, ss, name)
            check_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            msg = "本次更新的剧集为：%s%s已更新到：第%s集%s更新时间：%s" % (name, "\n\n", ep, "\n\n", check_time)
            yuntui_push(msg)
            time.sleep(10) # 可自定义时长，建议保留防止过多请求导致连接中断
    print("----------全部剧集已更新完成----------")