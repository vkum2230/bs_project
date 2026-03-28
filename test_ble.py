import socket

# 核心修改：使用通配符 MAC 地址
host_address = "00:00:00:00:00:00" 
port = 1  # 经典蓝牙 RFCOMM 通道

# 创建蓝牙套接字
server_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

try:
    # 绑定地址和端口
    # 注意：在某些新系统中，如果 "00:00:00:00:00:00" 仍报错，请尝试 "localhost"
    server_sock.bind((host_address, port))
    
    # 开始监听
    server_sock.listen(1)
    
    print("【系统就绪】正在等待手机连接...")
    print("提示：请确保手机已配对成功，并在 App 中点击‘连接’")

    # 接受手机的连接请求
    client_sock, client_info = server_sock.accept()
    print(f"【连接成功】手机地址: {client_info[0]}")

    client_sock.send(b"Connected to Pi5 Debian 13\r\n")

    while True:
        data = client_sock.recv(1024)
        if not data:
            break
        
        msg = data.decode('utf-8', errors='ignore').strip()
        print(f"收到手机消息: {msg}")

        # 回传数据
        reply = f"Pi5 Echo: {msg}\r\n"
        client_sock.send(reply.encode('utf-8'))

except Exception as e:
    print(f"发生错误: {e}")

finally:
    if 'client_sock' in locals():
        client_sock.close()
    server_sock.close()
    print("服务器已关闭")