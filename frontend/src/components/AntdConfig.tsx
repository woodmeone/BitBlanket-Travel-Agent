'use client';

/**
 * Ant Design runtime provider with global locale and theme defaults.
 * Use this component to keep UI behavior consistent across pages.
 */


import React from 'react';
import { ConfigProvider, App as AntApp } from 'antd';

const AntdConfig: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
        },
      }}
    >
      <AntApp>
        {children}
      </AntApp>
    </ConfigProvider>
  );
};

export default AntdConfig;
