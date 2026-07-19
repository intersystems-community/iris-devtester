class CPFPreset:
    ENABLE_CALLIN = "[Actions]\nModifyService:Name=%Service_CallIn,Enabled=1,AutheEnabled=48"

    CI_OPTIMIZED = "[config]\nglobals=0,0,256,0,0,0\ngmheap=64000"

    SECURE_DEFAULTS = (
        "[Actions]\n"
        "ModifyService:Name=%Service_CallIn,Enabled=1,AutheEnabled=48\n"
        "ModifyUser:Name=SuperUser,PasswordHash=FBFE8593AEFA510C27FD184738D6E865A441DE98,u4ocm4qh,ChangePassword=0,PasswordNeverExpires=1\n"
        "ModifyUser:Name=_SYSTEM,ChangePassword=0,PasswordNeverExpires=1"
    )
