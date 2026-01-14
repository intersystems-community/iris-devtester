class CPFPreset:
    ENABLE_CALLIN = (
        "[Actions]\n"
        "ModifyService:Name=%Service_CallIn,Enabled=1,AutheEnabled=48"
    )
    
    CI_OPTIMIZED = (
        "[config]\n"
        "globals=0,0,256,0,0,0\n"
        "gmheap=64000"
    )

    SECURE_DEFAULTS = (
        "[Actions]\n"
        "ModifyService:Name=%Service_CallIn,Enabled=1,AutheEnabled=48\n"
        "ModifyUser:Name=SuperUser,PasswordHash=FBFE8593AEFA510C27FD184738D6E865A441DE98,u4ocm4qh,ChangePassword=0,PasswordNeverExpires=1"
    )
