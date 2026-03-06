'use client';

import { Layout } from 'antd';
import ChatArea from '@/components/ChatArea';
import Sidebar from '@/components/Sidebar';

export default function Home() {
  return (
    <Layout style={{
      minHeight: '100vh',
      background: 'transparent'
    }}>
      <Layout.Sider
        width={280}
        theme="light"
        style={{
          borderRight: '1px solid rgba(102, 126, 234, 0.1)',
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
          background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
          boxShadow: '4px 0 20px rgba(102, 126, 234, 0.08)',
        }}
      >
        <Sidebar />
      </Layout.Sider>
      <Layout style={{
        marginLeft: 280,
        transition: 'margin-left 0.3s ease',
        background: 'transparent'
      }}>
        <Layout.Content style={{
          margin: 0,
          minHeight: '100vh',
          background: 'transparent'
        }}>
          <ChatArea />
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
