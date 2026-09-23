import { useState, useEffect } from 'react'
import {
  Card, Form, Input, Button, message, Avatar, Upload, Tabs, Descriptions,
  Modal, Row, Col
} from 'antd'
import {
  UserOutlined, LockOutlined, CameraOutlined, SafetyOutlined
} from '@ant-design/icons'
import { localAuthApi } from '@/api'
import { useAppStore } from '@/store/useStore'

const AccountSettings = () => {
  const { user } = useAppStore()
  const [form] = Form.useForm()
  const [pwdForm] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [pwdLoading, setPwdLoading] = useState(false)

  useEffect(() => {
    if (user) {
      form.setFieldsValue({
        username: user.username,
        email: user.email,
        avatar: user.avatar,
      })
    }
  }, [user])

  const handleSaveProfile = async (values: any) => {
    setLoading(true)
    try {
      const res: any = await localAuthApi.updateProfile({
        username: values.username,
        avatar: values.avatar,
      })
      message.success('保存成功')
      // 更新全局用户信息
      const state = useAppStore.getState()
      if (state.token && res.data) {
        state.setAuth(state.token, { ...state.user, ...res.data })
      }
    } catch (e: any) {
      message.error('保存失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const handleChangePassword = async (values: any) => {
    if (values.new_password !== values.confirm_password) {
      message.error('两次输入的新密码不一致')
      return
    }
    setPwdLoading(true)
    try {
      await localAuthApi.changePassword(values.old_password, values.new_password)
      message.success('密码修改成功')
      pwdForm.resetFields()
    } catch (e: any) {
      message.error('密码修改失败，请检查旧密码是否正确')
    } finally {
      setPwdLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2 style={{ marginBottom: 24 }}>账号设置</h2>

      <Tabs
        defaultActiveKey="profile"
        items={[
          {
            key: 'profile',
            label: <span><UserOutlined /> 基本信息</span>,
            children: (
              <Card>
                <Row gutter={24}>
                  <Col span={6} style={{ textAlign: 'center' }}>
                    <Upload
                      name="file"
                      showUploadList={false}
                      action="/geo/api/v1/upload/image"
                      headers={{ Authorization: `Bearer ${localStorage.getItem('geo_token')}` }}
                      onChange={async (info) => {
                        if (info.file.status === 'done') {
                          const url = info.file.response?.data?.url
                          if (url) {
                            form.setFieldsValue({ avatar: url })
                            message.success('头像上传成功，点击保存生效')
                          }
                        } else if (info.file.status === 'error') {
                          message.error('上传失败，请重试')
                        }
                      }}
                    >
                      <div style={{ position: 'relative', display: 'inline-block', cursor: 'pointer' }}>
                        <Avatar
                          size={100}
                          src={form.getFieldValue('avatar') || user?.avatar}
                          icon={<UserOutlined />}
                        />
                        <Button
                          type="text"
                          icon={<CameraOutlined />}
                          style={{
                            position: 'absolute',
                            bottom: 0,
                            right: 0,
                            background: '#fff',
                            borderRadius: '50%',
                          }}
                        />
                      </div>
                    </Upload>
                    <div style={{ marginTop: 12, color: '#64748B', fontSize: 13 }}>
                      点击上传头像
                    </div>
                  </Col>
                  <Col span={18}>
                    <Form
                      form={form}
                      layout="vertical"
                      onFinish={handleSaveProfile}
                    >
                      <Form.Item
                        name="username"
                        label="用户名"
                        rules={[{ required: true, message: '请输入用户名' }]}
                      >
                        <Input prefix={<UserOutlined />} />
                      </Form.Item>
                      <Form.Item name="email" label="邮箱">
                        <Input disabled />
                      </Form.Item>
                      <Form.Item name="avatar" label="头像URL">
                        <Input placeholder="头像图片URL" />
                      </Form.Item>
                      <Form.Item>
                        <Button type="primary" htmlType="submit" loading={loading}>
                          保存修改
                        </Button>
                      </Form.Item>
                    </Form>
                  </Col>
                </Row>
              </Card>
            ),
          },
          {
            key: 'security',
            label: <span><LockOutlined /> 修改密码</span>,
            children: (
              <Card>
                <Form
                  form={pwdForm}
                  layout="vertical"
                  onFinish={handleChangePassword}
                  style={{ maxWidth: 400 }}
                >
                  <Form.Item
                    name="old_password"
                    label="当前密码"
                    rules={[{ required: true, message: '请输入当前密码' }]}
                  >
                    <Input.Password prefix={<LockOutlined />} />
                  </Form.Item>
                  <Form.Item
                    name="new_password"
                    label="新密码"
                    rules={[
                      { required: true, message: '请输入新密码' },
                      { min: 6, message: '密码至少6位' },
                    ]}
                  >
                    <Input.Password prefix={<LockOutlined />} />
                  </Form.Item>
                  <Form.Item
                    name="confirm_password"
                    label="确认新密码"
                    rules={[{ required: true, message: '请再次输入新密码' }]}
                  >
                    <Input.Password prefix={<LockOutlined />} />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={pwdLoading}>
                      修改密码
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            ),
          },
          {
            key: 'info',
            label: <span><SafetyOutlined /> 账号信息</span>,
            children: (
              <Card>
                <Descriptions title="账号详情" column={1}>
                  <Descriptions.Item label="用户ID">{user?.id || '-'}</Descriptions.Item>
                  <Descriptions.Item label="用户名">{user?.username || '-'}</Descriptions.Item>
                  <Descriptions.Item label="邮箱">{user?.email || '-'}</Descriptions.Item>
                  <Descriptions.Item label="角色">{user?.role || '-'}</Descriptions.Item>
                  <Descriptions.Item label="注册时间">{user?.created_at || '-'}</Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
        ]}
      />
    </div>
  )
}

export default AccountSettings

