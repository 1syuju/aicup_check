-- AI CUP 2025 報到系統資料庫設定腳本
-- 適用於 SQL Server

-- 1. 建立資料庫（如果不存在）
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'AICUP2025_Checkin')
BEGIN
    CREATE DATABASE AICUP2025_Checkin
    COLLATE Chinese_Taiwan_Stroke_CI_AS;
END
GO

USE AICUP2025_Checkin;
GO

-- 2. 建立參加者表格
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[participants]') AND type in (N'U'))
BEGIN
    CREATE TABLE participants (
        id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(100) COLLATE Chinese_Taiwan_Stroke_CI_AS NOT NULL,
        email NVARCHAR(100) NULL,
        phone NVARCHAR(20) NULL,
        organization NVARCHAR(200) COLLATE Chinese_Taiwan_Stroke_CI_AS NULL,
        created_at DATETIME2 DEFAULT GETDATE()
    );
END
GO

-- 3. 建立報到記錄表格
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[checkin_logs]') AND type in (N'U'))
BEGIN
    CREATE TABLE checkin_logs (
        id INT IDENTITY(1,1) PRIMARY KEY,
        participant_id INT NOT NULL,
        checkin_time DATETIME2 DEFAULT GETDATE(),
        checkin_method NVARCHAR(20) DEFAULT 'manual',
        FOREIGN KEY (participant_id) REFERENCES participants(id)
    );
END
GO

-- 4. 建立索引以提升查詢效能
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_participants_name')
BEGIN
    CREATE INDEX IX_participants_name ON participants(name);
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_checkin_logs_participant_id')
BEGIN
    CREATE INDEX IX_checkin_logs_participant_id ON checkin_logs(participant_id);
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_checkin_logs_checkin_time')
BEGIN
    CREATE INDEX IX_checkin_logs_checkin_time ON checkin_logs(checkin_time);
END
GO

-- 5. 建立檢視以方便查詢報到狀態
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_participant_checkin_status')
BEGIN
    DROP VIEW v_participant_checkin_status;
END
GO

CREATE VIEW v_participant_checkin_status AS
SELECT 
    p.id,
    p.name,
    p.email,
    p.phone,
    p.organization,
    p.created_at,
    CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END AS is_checked_in,
    c.checkin_time,
    c.checkin_method
FROM participants p
LEFT JOIN checkin_logs c ON p.id = c.participant_id;
GO

-- 6. 建立預存程序以處理報到
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_checkin_participant')
BEGIN
    DROP PROCEDURE sp_checkin_participant;
END
GO

CREATE PROCEDURE sp_checkin_participant
    @participant_id INT,
    @checkin_method NVARCHAR(20) = 'manual'
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @participant_name NVARCHAR(100);
    DECLARE @already_checked_in BIT = 0;
    
    -- 檢查參加者是否存在
    SELECT @participant_name = name 
    FROM participants 
    WHERE id = @participant_id;
    
    IF @participant_name IS NULL
    BEGIN
        RAISERROR ('參加者不存在', 16, 1);
        RETURN;
    END
    
    -- 檢查是否已經報到
    IF EXISTS (SELECT 1 FROM checkin_logs WHERE participant_id = @participant_id)
    BEGIN
        SET @already_checked_in = 1;
    END
    
    -- 如果沒有報到，則記錄報到
    IF @already_checked_in = 0
    BEGIN
        INSERT INTO checkin_logs (participant_id, checkin_method)
        VALUES (@participant_id, @checkin_method);
        
        SELECT 
            'success' AS status,
            @participant_name + ' 報到成功！' AS message,
            @participant_name AS name,
            organization
        FROM participants 
        WHERE id = @participant_id;
    END
    ELSE
    BEGIN
        SELECT 
            'already_checked_in' AS status,
            @participant_name + ' 已經報到過了' AS message,
            @participant_name AS name,
            organization
        FROM participants 
        WHERE id = @participant_id;
    END
END
GO

-- 7. 建立預存程序以匯入參加者資料
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_import_participants')
BEGIN
    DROP PROCEDURE sp_import_participants;
END
GO

CREATE PROCEDURE sp_import_participants
    @name NVARCHAR(100),
    @email NVARCHAR(100) = NULL,
    @phone NVARCHAR(20) = NULL,
    @organization NVARCHAR(200) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    -- 檢查姓名是否已存在
    IF EXISTS (SELECT 1 FROM participants WHERE name = @name)
    BEGIN
        RAISERROR ('參加者姓名已存在: %s', 16, 1, @name);
        RETURN;
    END
    
    -- 插入新參加者
    INSERT INTO participants (name, email, phone, organization)
    VALUES (@name, @email, @phone, @organization);
    
    SELECT SCOPE_IDENTITY() AS new_id;
END
GO

-- 8. 建立預存程序以取得報到統計
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_get_checkin_stats')
BEGIN
    DROP PROCEDURE sp_get_checkin_stats;
END
GO

CREATE PROCEDURE sp_get_checkin_stats
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        COUNT(*) AS total_participants,
        COUNT(DISTINCT c.participant_id) AS checked_in_count,
        COUNT(*) - COUNT(DISTINCT c.participant_id) AS not_checked_in_count
    FROM participants p
    LEFT JOIN checkin_logs c ON p.id = c.participant_id;
END
GO

-- 9. 建立觸發器以記錄資料變更
IF EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_participants_audit')
BEGIN
    DROP TRIGGER tr_participants_audit;
END
GO

CREATE TRIGGER tr_participants_audit
ON participants
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- 這裡可以添加審計日誌邏輯
    -- 例如記錄誰在什麼時候修改了資料
END
GO

PRINT 'AI CUP 2025 報到系統資料庫設定完成！';
PRINT '請記得更新 Flask 應用程式的 DATABASE_URL 設定。';
GO
