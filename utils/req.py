# encoding=utf8
# 请求的方法
import httpx
from httpx import Limits
from typing import Union, List
import asyncio

from utils import default_header_user_agent

from utils.models import API
from utils.log import logger


def reqAPI(api: API, client: Union[httpx.Client, httpx.AsyncClient]) -> httpx.Response:
    if isinstance(api.data, dict):
        resp = client.request(method=api.method, json=api.data,
                              headers=api.header, url=api.url, timeout=10)
    else:
        resp = client.request(method=api.method, data=api.data,
                              headers=api.header, url=api.url, timeout=10)
    return resp


def reqFuncByProxy(api: Union[API, str], phone: Union[tuple, str], proxy: dict) -> bool:
    """通过代理请求接口方法"""
    # 多手机号支持
    if isinstance(phone, tuple):
        phone_lst = [_ for _ in phone]
    else:
        phone_lst = [phone]
    with httpx.Client(headers=default_header_user_agent(), verify=False, proxies=proxy) as client:
        for ph in phone_lst:
            try:
                if isinstance(api, API):
                    api = api.handle_API(ph)
                    resp = reqAPI(api, client)
                    logger.info(f"{api.desc}-{resp.text}")
                    logger.info(f"{api.desc}-{resp.text[:30]}")
                else:
                    api = api.replace("[phone]", ph).replace(" ", "").replace('\n', '').replace('\r', '')
                    resp = client.get(url=api, headers=default_header_user_agent())
                    logger.info(f"GETAPI接口-{resp.text}")
                    logger.info(f"GETAPI接口-{resp.text[:30]}")
                return True
            except httpx.HTTPError as why:
                logger.error(f"请求失败{why}")
                return False


def reqFunc(api: Union[API, str], phone: Union[tuple, str]) -> bool:
    """请求接口方法"""
    # 多手机号支持
    if isinstance(phone, tuple):
        phone_lst = [_ for _ in phone]
    else:
        phone_lst = [phone]
    with httpx.Client(headers=default_header_user_agent(), verify=False) as client:
        for ph in phone_lst:
            try:
                if isinstance(api, API):
                    api = api.handle_API(ph)
                    resp = reqAPI(api, client)
                    # logger.info(f"{api.desc}-{resp.text}")
                    # logger.info(f"{api.desc}:json:-{resp.json()}")

                    # 获取响应头信息
                    content_type = resp.headers.get('content-type', 'unknown')
                    # logger.info(f"{api.desc}: Content-Type - {content_type}")
                    # 获取响应体信息
                    if 'application/json' in content_type.lower():
                        json_data = resp.json()
                        # logger.info(f"{api.desc}: JSON data - {json_data}")
                        if 'success' in json_data:
                            logger.info(f"{api.desc}: Success - {json_data['success']} 这个 API 可以使用")
                        if 'code' in json_data and 'msg' in json_data:
                            if json_data['code'] == '200' and json_data["msg"] == '操作成功':
                                logger.info(f"{api.desc}: Success - {json_data['msg']} 这个 API 可以使用")
                            if json_data['code'] == '200' and json_data["msg"] == '发送成功':
                                logger.info(f"{api.desc}: Success - {json_data['msg']} 这个 API 可以使用")
                            if json_data['code'] == '200' and json_data["msg"] == '成功':
                                logger.info(f"{api.desc}: Success - {json_data['msg']} 这个 API 可以使用")
                        if json_data.get('msg'):
                            logger.info(f"Success - {json_data.get('msg')} ")
                    else:

                        if resp.text.find("success") != -1:
                            logger.info(f"{api.desc}: Response text - {resp.text[:20]}")
                        if resp.text.find("ok") != -1:
                            logger.info(f"{api.desc}: Response text - {resp.text[:20]}")
                    #     # logger.info(f"{api.desc}-{resp.text[:30]}")

                return True
            except httpx.HTTPError as why:
                # logger.error(f"请求失败{why}")
                # logger.error(f'失败！')
                return False


async def asyncReqs(src: Union[API, str], phone: Union[tuple, str], semaphore):
    """异步请求方法

    :param:
    :return:

    """
    # 多手机号支持
    if isinstance(phone, tuple):
        phone_lst = [_ for _ in phone]
    else:
        phone_lst = [phone]
    async with semaphore:
        async with httpx.AsyncClient(
                limits=Limits(max_connections=1000,
                              max_keepalive_connections=2000),
                headers=default_header_user_agent(),
                verify=False,
                timeout=99999
        ) as c:

            for ph in phone_lst:
                try:
                    if isinstance(src, API):
                        src = src.handle_API(ph)
                        r = await reqAPI(src, c)
                    else:
                        # 利用元组传参安全因为元组不可修改
                        s = (src.replace(" ", "").replace("\n", "").replace("\t", "").replace(
                            "&amp;", "").replace('\n', '').replace('\r', ''),)
                        r = await c.get(*s)
                    return r
                except httpx.HTTPError as why:
                    logger.error(f"异步请求失败{type(why)}")
                    # logger.error(f"异步请求失败{why}")
                    # import aiofiles
                    # async with aiofiles.open("error.txt","a",encoding="utf-8") as f:
                    #     await f.write(f"{str(s[0]) if str(s[0]) else str(src)}\n")
                except TypeError:
                    logger.error("类型错误")
                except Exception as wy:
                    logger.exception(f"异步失败{wy}")


def callback(result):
    """异步回调函数"""
    log = result.result()
    if log is not None:
        logger.info(f"请求结果:{log.text[:30]}")


async def runAsync(apis: List[Union[API, str]], phone: Union[tuple, str]):
    tasks = []

    for api in apis:
        semaphore = asyncio.Semaphore(999999)
        task = asyncio.ensure_future(asyncReqs(api, phone, semaphore))
        task.add_done_callback(callback)
        tasks.append(task)

    await asyncio.gather(
        *tasks
    )
