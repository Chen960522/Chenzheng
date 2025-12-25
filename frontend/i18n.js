// Internationalization (i18n) Module

const translations = {
    en: {
        app: {
            title: 'AWS Pricing Assistant',
            subtitle: 'AI-Powered Cloud Pricing Tool'
        },
        nav: {
            dashboard: 'Dashboard',
            newQuote: 'New Quote',
            history: 'History',
            users: 'Users',
            logout: 'Logout'
        },
        login: {
            username: 'Username',
            password: 'Password',
            submit: 'Login',
            error: 'Login failed. Please check your credentials.'
        },
        dashboard: {
            title: 'Dashboard',
            subtitle: 'Quick actions and recent quotes',
            newQuote: 'Create New Quote',
            newQuoteDesc: 'Convert cloud configurations to AWS pricing',
            startBtn: 'Start Now',
            viewHistory: 'View History',
            viewHistoryDesc: 'Access your previous quotes',
            viewBtn: 'View All',
            recentQuotes: 'Recent Quotes',
            noQuotes: 'No quotes yet',
            createFirst: 'Create Your First Quote'
        },
        quote: {
            title: 'Create New Quote',
            subtitle: 'Enter cloud configuration or upload a file',
            configInput: 'Configuration Input',
            configLabel: 'Cloud Configuration',
            configPlaceholder: 'Enter configuration in JSON, YAML, CSV, or plain text...',
            configHint: 'Supports Alibaba Cloud, Huawei Cloud, Tencent Cloud, GCP, and Azure configurations',
            orUpload: 'Or Upload File',
            chooseFile: 'Choose File',
            preferences: 'Preferences',
            region: 'AWS Region',
            pricingModel: 'Pricing Model',
            onDemand: 'On-Demand',
            reserved: 'Reserved Instance',
            savingsPlan: 'Savings Plan',
            notes: 'Notes (Optional)',
            notesPlaceholder: 'Add any additional notes...',
            generate: 'Generate Quote',
            processing: 'Processing Your Request'
        },
        result: {
            title: 'Quote Result',
            downloadPdf: 'Download PDF',
            downloadExcel: 'Download Excel',
            downloadJson: 'Download JSON',
            summary: 'Summary',
            quoteId: 'Quote ID:',
            createdAt: 'Created:',
            region: 'Region:',
            monthlyTotal: 'Monthly Total:',
            annualTotal: 'Annual Total:',
            mappings: 'Service Mappings',
            breakdown: 'Pricing Breakdown',
            notes: 'Notes',
            newQuote: 'Create New Quote',
            service: 'Service',
            pricingModel: 'Pricing Model',
            monthly: 'Monthly Cost',
            annual: 'Annual Cost'
        },
        history: {
            title: 'Quote History',
            subtitle: 'View and manage your previous quotes',
            search: 'Search quotes...',
            status: 'Status:',
            allStatus: 'All',
            draft: 'Draft',
            finalized: 'Finalized',
            sent: 'Sent',
            empty: 'No quotes found',
            createFirst: 'Create Your First Quote',
            deleteTitle: 'Delete Quote',
            deleteConfirm: 'Are you sure you want to delete this quote?'
        },
        users: {
            title: 'User Management',
            createUser: 'Create User',
            username: 'Username',
            email: 'Email',
            fullName: 'Full Name',
            password: 'Password',
            passwordHint: 'Minimum 8 characters, include uppercase, lowercase, number, and special character',
            role: 'Role',
            roleSales: 'Sales',
            roleAdmin: 'Admin',
            active: 'Active',
            inactive: 'Inactive',
            status: 'Status',
            actions: 'Actions',
            noUsers: 'No users found',
            resetPassword: 'Reset Password',
            resetPasswordConfirm: 'Generate a new temporary password for this user?',
            tempPasswordLabel: 'Temporary Password:',
            copyPassword: 'Copy',
            deleteUser: 'Delete User',
            deleteConfirm: 'Are you sure you want to delete this user?'
        },
        common: {
            loading: 'Loading...',
            cancel: 'Cancel',
            save: 'Save',
            delete: 'Delete',
            edit: 'Edit',
            view: 'View',
            back: 'Back',
            confirm: 'Confirm',
            loadError: 'Failed to load data'
        }
    },
    zh: {
        app: {
            title: 'AWS 智能定价助手',
            subtitle: 'AI 驱动的云定价工具'
        },
        nav: {
            dashboard: '仪表板',
            newQuote: '新建报价',
            history: '历史记录',
            users: '用户管理',
            logout: '退出登录'
        },
        login: {
            username: '用户名',
            password: '密码',
            submit: '登录',
            error: '登录失败，请检查您的凭据。'
        },
        dashboard: {
            title: '仪表板',
            subtitle: '快速操作和最近报价',
            newQuote: '创建新报价',
            newQuoteDesc: '将云配置转换为 AWS 定价',
            startBtn: '立即开始',
            viewHistory: '查看历史',
            viewHistoryDesc: '访问您之前的报价',
            viewBtn: '查看全部',
            recentQuotes: '最近报价',
            noQuotes: '暂无报价',
            createFirst: '创建您的第一个报价'
        },
        quote: {
            title: '创建新报价',
            subtitle: '输入云配置或上传文件',
            configInput: '配置输入',
            configLabel: '云配置',
            configPlaceholder: '输入 JSON、YAML、CSV 或纯文本格式的配置...',
            configHint: '支持阿里云、华为云、腾讯云、GCP 和 Azure 配置',
            orUpload: '或上传文件',
            chooseFile: '选择文件',
            preferences: '偏好设置',
            region: 'AWS 区域',
            pricingModel: '定价模型',
            onDemand: '按需付费',
            reserved: '预留实例',
            savingsPlan: '节省计划',
            notes: '备注（可选）',
            notesPlaceholder: '添加任何额外备注...',
            generate: '生成报价',
            processing: '正在处理您的请求'
        },
        result: {
            title: '报价结果',
            downloadPdf: '下载 PDF',
            downloadExcel: '下载 Excel',
            downloadJson: '下载 JSON',
            summary: '摘要',
            quoteId: '报价 ID：',
            createdAt: '创建时间：',
            region: '区域：',
            monthlyTotal: '月度总计：',
            annualTotal: '年度总计：',
            mappings: '服务映射',
            breakdown: '定价明细',
            notes: '备注',
            newQuote: '创建新报价',
            service: '服务',
            pricingModel: '定价模型',
            monthly: '月度成本',
            annual: '年度成本'
        },
        history: {
            title: '报价历史',
            subtitle: '查看和管理您之前的报价',
            search: '搜索报价...',
            status: '状态：',
            allStatus: '全部',
            draft: '草稿',
            finalized: '已完成',
            sent: '已发送',
            empty: '未找到报价',
            createFirst: '创建您的第一个报价',
            deleteTitle: '删除报价',
            deleteConfirm: '您确定要删除此报价吗？'
        },
        users: {
            title: '用户管理',
            createUser: '创建用户',
            username: '用户名',
            email: '邮箱',
            fullName: '全名',
            password: '密码',
            passwordHint: '至少 8 个字符，包含大写、小写、数字和特殊字符',
            role: '角色',
            roleSales: '销售',
            roleAdmin: '管理员',
            active: '活跃',
            inactive: '未激活',
            status: '状态',
            actions: '操作',
            noUsers: '未找到用户',
            resetPassword: '重置密码',
            resetPasswordConfirm: '为此用户生成新的临时密码？',
            tempPasswordLabel: '临时密码：',
            copyPassword: '复制',
            deleteUser: '删除用户',
            deleteConfirm: '您确定要删除此用户吗？'
        },
        common: {
            loading: '加载中...',
            cancel: '取消',
            save: '保存',
            delete: '删除',
            edit: '编辑',
            view: '查看',
            back: '返回',
            confirm: '确认',
            loadError: '加载数据失败'
        }
    }
};

// Get current language from localStorage or default to English
function getCurrentLanguage() {
    return localStorage.getItem('language') || 'en';
}

// Set current language
function setLanguage(lang) {
    localStorage.setItem('language', lang);
    updateTranslations();
    updateLanguageButtons();
}

// Get translation for a key
function t(key) {
    const lang = getCurrentLanguage();
    const keys = key.split('.');
    let value = translations[lang];

    for (const k of keys) {
        if (value && typeof value === 'object') {
            value = value[k];
        } else {
            return key; // Return key if translation not found
        }
    }

    return value || key;
}

// Update all translations on the page
function updateTranslations() {
    const lang = getCurrentLanguage();
    
    // Update elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        element.textContent = t(key);
    });

    // Update placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        element.placeholder = t(key);
    });

    // Update HTML lang attribute
    document.documentElement.lang = lang;
}

// Update language button states
function updateLanguageButtons() {
    const lang = getCurrentLanguage();
    
    document.querySelectorAll('.lang-btn').forEach(btn => {
        const btnLang = btn.getAttribute('data-lang');
        if (btnLang === lang) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Initialize i18n
document.addEventListener('DOMContentLoaded', () => {
    // Set up language switcher buttons
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const lang = btn.getAttribute('data-lang');
            setLanguage(lang);
        });
    });

    // Initial translation update
    updateTranslations();
    updateLanguageButtons();
});
