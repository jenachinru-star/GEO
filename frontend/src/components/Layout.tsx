import { useState, useEffect } from 'react'
import { Layout, Menu, Avatar, Dropdown, Badge, Button, Tooltip, message } from 'antd'
import {
  DashboardOutlined,
  MonitorOutlined,
  FileTextOutlined,
  BookOutlined,
  TeamOutlined,
  RobotOutlined,
  SettingOutlined,
  BellOutlined,
  ReloadOutlined,
  SyncOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LoginOutlined,
  LogoutOutlined,
  AppstoreOutlined
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAppStore } from '@/store/useStore'
import { authApi } from '@/api'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '数据概览' },
  { key: '/semantic', icon: <FileTextOutlined />, label: '语义库' },
  { key: '/content', icon: <AppstoreOutlined />, label: '内容中心' },
  { key: '/data', icon: <MonitorOutlined />, label: '数据中心' },
  { key: '/tasks', icon: <SyncOutlined />, label: '任务中心' },
]

const MainLayout = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { systemInfo, user, clearAuth } = useAppStore()

  const selectedKey = location.pathname

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  const handleRefresh = () => {
    window.location.reload()
  }

  const handleLogin = async () => {
    try {
      const res: any = await authApi.getIamUrl()
      window.location.href = res.data.auth_url
    } catch (e) {
      message.error('获取登录地址失败')
    }
  }

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } catch (e) {
      // 忽略登出接口错误
    }
    clearAuth()
    message.success('已退出登录')
    navigate('/dashboard')
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={220}
        style={{
          background: '#FFFFFF',
          borderRight: '1px solid var(--border-color)',
          position: 'sticky',
          top: 0,
          height: '100vh',
          overflow: 'auto',
          boxShadow: '2px 0 8px rgba(0,0,0,0.03)'
        }}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: collapsed ? 14 : 17,
          fontWeight: 700,
          borderBottom: '1px solid var(--border-color)',
          letterSpacing: 0.5,
          background: 'var(--primary-gradient)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
        }}>
          {collapsed ? 'GEO' : 'GEO 创作者中心'}
        </div>
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={handleMenuClick}
          className="sider-menu-light"
          style={{ background: 'transparent', borderRight: 0, marginTop: 12, padding: '0 4px' }}
        />
        {!collapsed && user && (
          <div style={{
            position: 'absolute',
            bottom: 16,
            left: 0,
            right: 0,
            padding: '0 16px',
            color: 'var(--text-tertiary)',
            fontSize: 11
          }}>
            <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{user.username}</div>
          </div>
        )}
      </Sider>
      <Layout>
        <Header
          className="header-glass"
          style={{
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 100
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
            />
            <span style={{ fontSize: 15, fontWeight: 500, color: '#0F172A' }}>
              {'GEO 创作者中心'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Tooltip title="刷新页面">
              <Button type="text" icon={<ReloadOutlined />} onClick={handleRefresh} />
            </Tooltip>
            <Badge count={0} size="small">
              <Button type="text" icon={<BellOutlined />} />
            </Badge>
            {user ? (
              <Dropdown menu={{
                items: [
                  { key: 'profile', icon: <UserOutlined />, label: '个人资料', onClick: () => navigate('/profile') },
                  { key: 'settings', icon: <SettingOutlined />, label: '账号设置', onClick: () => navigate('/settings') },
                  { type: 'divider' },
                  { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout }
                ]
              }}>
                <Avatar style={{ background: 'var(--primary-gradient)', cursor: 'pointer' }}>
                  {user.username?.charAt(0)?.toUpperCase()}
                </Avatar>
              </Dropdown>
            ) : (
              <Button
                type="primary"
                icon={<LoginOutlined />}
                onClick={handleLogin}
                className="btn-primary-gradient"
              >
                IAM登录
              </Button>
            )}
          </div>
        </Header>
        <Content style={{ margin: 0, minHeight: 'calc(100vh - 64px)', background: 'var(--bg-page)' }}>
          <div className="page-content">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout
