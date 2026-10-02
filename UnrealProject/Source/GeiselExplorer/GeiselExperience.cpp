#include "GeiselExperience.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/Canvas.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"

AGeiselGameMode::AGeiselGameMode()
{
    DefaultPawnClass = AGeiselCharacter::StaticClass();
    HUDClass = AGeiselHUD::StaticClass();
}

AGeiselCharacter::AGeiselCharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    GetCapsuleComponent()->InitCapsuleSize(32,92);
    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("VisitorCamera"));
    Camera->SetupAttachment(GetCapsuleComponent());
    Camera->SetRelativeLocation(FVector(0,0,64));
    Camera->bUsePawnControlRotation = true;
    Camera->FieldOfView = 63;
    Camera->PostProcessBlendWeight = 1;
    bUseControllerRotationYaw = true;
    GetCharacterMovement()->MaxWalkSpeed = 360;
    GetCharacterMovement()->MaxFlySpeed = 1800;
    GetCharacterMovement()->BrakingDecelerationFlying = 2800;
    GetCharacterMovement()->MaxStepHeight = 42;
    GetCharacterMovement()->SetWalkableFloorAngle(48);
    GetCharacterMovement()->JumpZVelocity = 350;
}

void AGeiselCharacter::BeginPlay()
{
    Super::BeginPlay();
    GetCharacterMovement()->SetMovementMode(MOVE_Flying);
    if (auto* PC = Cast<APlayerController>(GetController()))
    {
        PC->SetInputMode(FInputModeGameOnly());
        PC->bShowMouseCursor = false;
    }
    auto& P = Camera->PostProcessSettings;
    P.bOverride_AutoExposureMethod = true; P.AutoExposureMethod = AEM_Histogram;
    P.bOverride_AutoExposureMinBrightness = true; P.AutoExposureMinBrightness = 10;
    P.bOverride_AutoExposureMaxBrightness = true; P.AutoExposureMaxBrightness = 16;
    P.bOverride_AutoExposureBias = true; P.AutoExposureBias = 0.1f;
    P.bOverride_MotionBlurAmount = true; P.MotionBlurAmount = 0;
    P.bOverride_BloomIntensity = true; P.BloomIntensity = 0.22f;
    P.bOverride_VignetteIntensity = true; P.VignetteIntensity = 0.17f;
    P.bOverride_WhiteTemp = true; P.WhiteTemp = 6000;
    P.bOverride_AutoExposureSpeedUp = true; P.AutoExposureSpeedUp = 4;
    P.bOverride_AutoExposureSpeedDown = true; P.AutoExposureSpeedDown = 3;
    ApplyLight();
    SetView(0);
    bTest = FParse::Param(FCommandLine::Get(), TEXT("GeiselSelfTest"));
    UE_LOG(LogTemp, Display, TEXT("[GEISEL] EXPERIENCE_READY views=4 lighting=3 collision=enabled mode=flight"));
}

void AGeiselCharacter::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindAxis("Forward",this,&AGeiselCharacter::Forward);
    Input->BindAxis("Right",this,&AGeiselCharacter::Right);
    Input->BindAxis("Rise",this,&AGeiselCharacter::Rise);
    Input->BindAxis("Yaw",this,&AGeiselCharacter::Yaw);
    Input->BindAxis("Pitch",this,&AGeiselCharacter::Pitch);
    Input->BindAxis("Zoom",this,&AGeiselCharacter::Zoom);
    Input->BindAction("Fast",IE_Pressed,this,&AGeiselCharacter::Fast);
    Input->BindAction("Fast",IE_Released,this,&AGeiselCharacter::Slow);
    Input->BindAction("Mode",IE_Pressed,this,&AGeiselCharacter::Mode);
    Input->BindAction("Light",IE_Pressed,this,&AGeiselCharacter::Light);
    Input->BindAction("Photo",IE_Pressed,this,&AGeiselCharacter::Photo);
    Input->BindAction("Help",IE_Pressed,this,&AGeiselCharacter::Help);
    Input->BindAction("View1",IE_Pressed,this,&AGeiselCharacter::View1);
    Input->BindAction("View2",IE_Pressed,this,&AGeiselCharacter::View2);
    Input->BindAction("View3",IE_Pressed,this,&AGeiselCharacter::View3);
    Input->BindAction("View4",IE_Pressed,this,&AGeiselCharacter::View4);
    Input->BindAction("Shot",IE_Pressed,this,&AGeiselCharacter::Shot);
    Input->BindAction("Exit",IE_Pressed,this,&AGeiselCharacter::Exit);
    Input->BindAction("Jump",IE_Pressed,this,&AGeiselCharacter::Hop);
}
void AGeiselCharacter::Forward(float V)
{
    if (Controller && V != 0) AddMovementInput((bFly ? Controller->GetControlRotation() : FRotator(0,Controller->GetControlRotation().Yaw,0)).Vector(),V);
}
void AGeiselCharacter::Right(float V)
{
    if (Controller && V != 0) AddMovementInput(FRotationMatrix(FRotator(0,Controller->GetControlRotation().Yaw,0)).GetUnitAxis(EAxis::Y),V);
}
void AGeiselCharacter::Rise(float V) { if (bFly && V != 0) AddMovementInput(FVector::UpVector,V); }
void AGeiselCharacter::Yaw(float V) { AddControllerYawInput(V); }
void AGeiselCharacter::Pitch(float V) { AddControllerPitchInput(V); }
void AGeiselCharacter::Zoom(float V) { if (V != 0) Camera->SetFieldOfView(FMath::Clamp(Camera->FieldOfView-V*3,35.0f,90.0f)); }
void AGeiselCharacter::Fast() { GetCharacterMovement()->MaxWalkSpeed=720; GetCharacterMovement()->MaxFlySpeed=4200; }
void AGeiselCharacter::Slow() { GetCharacterMovement()->MaxWalkSpeed=360; GetCharacterMovement()->MaxFlySpeed=1800; }
void AGeiselCharacter::Mode()
{
    if (bFly) SetWalking();
    else { bFly=true; GetCharacterMovement()->SetMovementMode(MOVE_Flying); Status=TEXT("FREE EXPLORATION"); }
}
bool AGeiselCharacter::SetWalking()
{
    FVector Target=GetActorLocation();
    for (TActorIterator<AActor> It(GetWorld());It;++It) if (It->ActorHasTag("WalkStart")) { Target=It->GetActorLocation();break; }
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(GeiselGround),true,this);
    if (!GetWorld()->LineTraceSingleByChannel(Hit,Target+FVector(0,0,1200),Target-FVector(0,0,12000),ECC_Visibility,Params)) return false;
    GetCharacterMovement()->StopMovementImmediately();
    SetActorLocation(Hit.ImpactPoint+FVector(0,0,95),false,nullptr,ETeleportType::TeleportPhysics);
    bFly=false; GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    if(Controller) Controller->SetControlRotation(FRotator(7,155,0));
    Camera->SetFieldOfView(68);
    Status=TEXT("ON THE SNAKE PATH");
    return true;
}
void AGeiselCharacter::Light() { LightPreset=(LightPreset+1)%3; ApplyLight(); }
FString AGeiselCharacter::LightName() const
{
    const TCHAR* Names[]={TEXT("09:00  MORNING"),TEXT("17:15  GOLDEN HOUR"),TEXT("19:05  BLUE HOUR")};
    return Names[LightPreset];
}
void AGeiselCharacter::ApplyLight()
{
    // NOAA solar geometry: 2026-09-30 PDT, 32.88116 N, 117.23765 W.
    // Outgoing rays in X-east/Y-south coordinates. At blue hour the sun is
    // below the terrain horizon; retaining its source illuminates atmosphere.
    const FRotator Angles[]={FRotator(-27.137072f,-156.364926f,0),FRotator(-15.680677f,-14.398049f,0),FRotator(7.214272f,.917663f,0)};
    const float Lux[]={65000,22000,20000};
    const float Temperatures[]={5600,3900,8500};
    for(TActorIterator<ADirectionalLight> It(GetWorld());It;++It)
    {
        It->SetActorRotation(Angles[LightPreset]);
        auto* C=Cast<UDirectionalLightComponent>(It->GetLightComponent());
        C->SetIntensity(Lux[LightPreset]); C->SetTemperature(Temperatures[LightPreset]); C->SetUseTemperature(true);
        // Keep the below-horizon atmospheric source for twilight scattering,
        // but exclude its direct rays from all scene surfaces after sunset.
        C->SetLightingChannels(LightPreset!=2,false,false);
        C->SetCastShadows(LightPreset!=2);
    }
    for(TActorIterator<ASkyLight> It(GetWorld());It;++It)
    {
        It->GetLightComponent()->SetIntensity(LightPreset==2?1.35f:1.0f);
        It->GetLightComponent()->RecaptureSky();
    }
    Camera->PostProcessSettings.AutoExposureMinBrightness=LightPreset==2?2.0f:10.0f;
    Camera->PostProcessSettings.AutoExposureMaxBrightness=LightPreset==2?7.0f:16.0f;
    Camera->PostProcessSettings.AutoExposureBias=LightPreset==2?0.45f:0.1f;
    Camera->PostProcessSettings.WhiteTemp=LightPreset==1?6200:6000;
    UE_LOG(LogTemp,Display,TEXT("[GEISEL] LIGHT_PRESET=%d %s"),LightPreset,*LightName());
}
void AGeiselCharacter::Photo() { bPhoto=!bPhoto; }
void AGeiselCharacter::Help() { bHelp=!bHelp; }
void AGeiselCharacter::View1() { SetView(0); } void AGeiselCharacter::View2() { SetView(1); }
void AGeiselCharacter::View3() { SetView(2); } void AGeiselCharacter::View4() { SetView(3); }
void AGeiselCharacter::SetView(int32 Index)
{
    const FName Tag(*FString::Printf(TEXT("View%d"),Index+1));
    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        if(!It->ActorHasTag(Tag)) continue;
        GetCharacterMovement()->StopMovementImmediately();
        bFly=true; GetCharacterMovement()->SetMovementMode(MOVE_Flying);
        SetActorLocation(It->GetActorLocation()-FVector(0,0,64),false,nullptr,ETeleportType::TeleportPhysics);
        if(Controller) Controller->SetControlRotation(It->GetActorRotation());
        const TCHAR* Names[]={TEXT("EAST CANYON"),TEXT("SNAKE PATH"),TEXT("SOUTH ELEVATION"),TEXT("ABOVE THE EUCALYPTUS"),TEXT("SNAKE COIL"),TEXT("SOUTH ENTRANCE REVIEW"),TEXT("NORTH APPROACH REVIEW"),TEXT("SOUTH APPROACH REVIEW")};
        Status=Index>=0 && Index<UE_ARRAY_COUNT(Names)?Names[Index]:TEXT("SNAKE COIL"); ViewIndex=Index;
        Camera->SetFieldOfView(Index==2?67:63);
        UE_LOG(LogTemp,Display,TEXT("[GEISEL] VIEW=%d position=%s"),Index+1,*GetActorLocation().ToCompactString());
        return;
    }
    UE_LOG(LogTemp,Error,TEXT("[GEISEL] Missing viewpoint %d"),Index+1);
}
void AGeiselCharacter::Capture(const FString& Name)
{
    const FString Folder=FPaths::ProjectSavedDir()/TEXT("Screenshots/Geisel");
    IFileManager::Get().MakeDirectory(*Folder,true);
    FScreenshotRequest::RequestScreenshot(Folder/Name+TEXT(".png"),false,false);
}
void AGeiselCharacter::Shot() { Capture(FString::Printf(TEXT("Geisel_%s"),*FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S")))); }
void AGeiselCharacter::Exit() { UKismetSystemLibrary::QuitGame(this,Cast<APlayerController>(GetController()),EQuitPreference::Quit,false); }
void AGeiselCharacter::Hop() { if(bFly) Rise(1); else Jump(); }

void AGeiselCharacter::Check(bool Passed,const TCHAR* Name,const FString& Detail)
{
    if(!Passed) bTestFailed=true;
    UE_LOG(LogTemp,Display,TEXT("[GEISEL_SELFTEST] %s %s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),Name,*Detail);
}
void AGeiselCharacter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(GetActorLocation().Z < -3500) SetView(1);
    if(bTest) SelfTest(DeltaSeconds);
}
void AGeiselCharacter::SelfTest(float DT)
{
    TestTime+=DT;
    if(TestPhase==0 && TestTime>12)
    {
        Check(ViewIndex==0,TEXT("initial_view")); bPhoto=true; Capture(TEXT("01_East_Canyon_Daylight"));
        TestLocation=GetActorLocation(); TestTime=0; TestPhase=1;
    }
    else if(TestPhase==1)
    {
        Forward(1);
        if(TestTime>1.2f) { Check(FVector::Distance(TestLocation,GetActorLocation())>200,TEXT("flight_movement")); SetView(1); TestTime=0; TestPhase=2; }
    }
    else if(TestPhase==2 && TestTime>8)
    {
        Check(ViewIndex==1 && FVector::Distance(TestLocation,GetActorLocation())>100,TEXT("view_switch"));
        Capture(TEXT("02_Snake_Path_Daylight"));
        TestTime=0; TestPhase=20;
    }
    else if(TestPhase==20 && TestTime>.3f)
    {
        Light(); Check(LightPreset==1,TEXT("golden_hour")); SetView(0); TestTime=0; TestPhase=3;
    }
    else if(TestPhase==3 && TestTime>9) { Capture(TEXT("03_East_Canyon_Golden_Hour")); TestTime=0; TestPhase=30; }
    else if(TestPhase==30 && TestTime>.3f) { SetView(2); TestTime=0; TestPhase=4; }
    else if(TestPhase==4 && TestTime>7) { Capture(TEXT("04_Library_Plaza")); TestTime=0; TestPhase=40; }
    else if(TestPhase==40 && TestTime>.3f) { Light(); SetView(0); TestTime=0; TestPhase=5; }
    else if(TestPhase==5 && TestTime>10)
    {
        Check(LightPreset==2,TEXT("blue_hour")); Capture(TEXT("05_East_Canyon_Blue_Hour"));
        TestTime=0; TestPhase=50;
    }
    else if(TestPhase==50 && TestTime>.3f)
    {
        Light(); Check(SetWalking(),TEXT("ground_trace")); WalkLocation=GetActorLocation(); TestTime=0; TestPhase=6;
    }
    else if(TestPhase==6)
    {
        Forward(0.5f);
        if(TestTime>2.5f)
        {
            Check(!bFly && GetCharacterMovement()->IsMovingOnGround(),TEXT("walk_grounded"),GetActorLocation().ToCompactString());
            Check(FVector::Dist2D(WalkLocation,GetActorLocation())>100,TEXT("walk_movement"));
            Photo(); Check(!bPhoto,TEXT("photo_toggle")); bHelp=true; TestTime=0; TestPhase=7;
        }
    }
    else if(TestPhase==7 && TestTime>5)
    {
        Capture(TEXT("06_Interactive_Walk")); TestTime=0; TestPhase=70;
    }
    else if(TestPhase==70 && TestTime>.3f) { SetView(3); bPhoto=true; TestTime=0; TestPhase=8; }
    else if(TestPhase==8 && TestTime>7) { Capture(TEXT("07_Aerial_Site")); TestTime=0; TestPhase=9; }
    else if(TestPhase==9 && TestTime>1)
    {
        int32 Probes=0, PavedHits=0;
        for(TActorIterator<AActor> It(GetWorld());It;++It)
        {
            if(!It->ActorHasTag(TEXT("SnakePavingProbe"))) continue;
            ++Probes;
            const FVector Point=It->GetActorLocation();
            FHitResult Hit;
            FCollisionQueryParams Params(SCENE_QUERY_STAT(SnakeCoilPaving),true,this);
            if(GetWorld()->LineTraceSingleByChannel(Hit,Point+FVector(0,0,150),Point-FVector(0,0,150),ECC_Visibility,Params)
                && Hit.GetActor() && Hit.GetActor()->ActorHasTag(TEXT("GeiselSnakePaving"))) ++PavedHits;
        }
        Check(Probes>=30 && PavedHits==Probes,TEXT("snake_coil_continuous_paving"),FString::Printf(TEXT("%d/%d paved probes"),PavedHits,Probes));
        SetView(4); TestTime=0; TestPhase=10;
    }
    else if(TestPhase==10 && TestTime>8)
    {
        Check(ViewIndex==4,TEXT("snake_coil_review_view"));
        Capture(TEXT("08_Snake_Coil_Continuity")); TestTime=0; TestPhase=11;
    }
    else if(TestPhase==11 && TestTime>3)
    {
        int32 ClearBollardPositions=0, ApproachFrames=0;
        for(float X : {-800.0f,800.0f})
        {
            FHitResult Hit;
            FCollisionQueryParams Params(SCENE_QUERY_STAT(SouthEntranceClearance),true,this);
            if(!GetWorld()->LineTraceSingleByChannel(Hit,FVector(X,2390,1130),FVector(X,2390,980),ECC_Visibility,Params)) ++ClearBollardPositions;
        }
        for(TActorIterator<AActor> It(GetWorld());It;++It)
        {
            const auto* MeshActor=Cast<AStaticMeshActor>(*It);
            const UStaticMesh* SiteMesh=nullptr;
            if(MeshActor) SiteMesh=MeshActor->GetStaticMeshComponent()->GetStaticMesh();
            if(SiteMesh && SiteMesh->GetName().Contains(TEXT("CAMPUS_LowConcreteGardenEdges"))) ++ApproachFrames;
        }
        Check(ClearBollardPositions==2,TEXT("south_entrance_floating_bollards_absent"),FString::Printf(TEXT("%d/2 clear positions"),ClearBollardPositions));
        Check(ApproachFrames==0,TEXT("unsupported_snake_approach_frames_absent"));
        SetView(5); TestTime=0; TestPhase=12;
    }
    else if(TestPhase==12 && TestTime>7)
    {
        Check(ViewIndex==5,TEXT("south_entrance_review_view"));
        Capture(TEXT("09_South_Entrance_Clearance")); TestTime=0; TestPhase=120;
    }
    else if(TestPhase==120 && TestTime>.3f) { SetView(6); TestTime=0; TestPhase=13; }
    else if(TestPhase==13 && TestTime>7)
    {
        Check(ViewIndex==6,TEXT("snake_north_approach_review_view"));
        Capture(TEXT("10_Snake_Approach_North")); TestTime=0; TestPhase=130;
    }
    else if(TestPhase==130 && TestTime>.3f) { SetView(7); TestTime=0; TestPhase=14; }
    else if(TestPhase==14 && TestTime>7)
    {
        Check(ViewIndex==7,TEXT("snake_south_approach_review_view"));
        Capture(TEXT("11_Snake_Approach_South")); TestTime=0; TestPhase=15;
    }
    else if(TestPhase==15 && TestTime>3)
    {
        UE_LOG(LogTemp,Display,TEXT("[GEISEL_SELFTEST] %s"),bTestFailed?TEXT("FAILED"):TEXT("ALL_PASSED")); Exit(); bTest=false;
    }
}

void AGeiselHUD::DrawHUD()
{
    Super::DrawHUD();
    const auto* P=Cast<AGeiselCharacter>(GetOwningPawn());
    if(!Canvas || !GEngine || !P || P->bPhoto) return;
    const float S=FMath::Clamp(Canvas->ClipX/1920.0f,0.75f,1.5f);
    const float X=36*S,Y=32*S;
    const FLinearColor Ink(.89f,.91f,.86f,1),Muted(.57f,.67f,.65f,1),Gold(.82f,.68f,.43f,1);
    DrawRect(FLinearColor(.017f,.028f,.03f,.76f),X,Y,405*S,122*S);
    DrawRect(Gold,X,Y,3*S,122*S);
    DrawText(TEXT("UC SAN DIEGO"),Gold,X+20*S,Y+15*S,GEngine->GetSmallFont(),.95f*S,false);
    DrawText(TEXT("GEISEL LIBRARY"),Ink,X+18*S,Y+41*S,GEngine->GetLargeFont(),2.0f*S,false);
    DrawText(TEXT("William L. Pereira  /  1970"),Muted,X+20*S,Y+87*S,GEngine->GetSmallFont(),.9f*S,false);
    const FString Info=FString::Printf(TEXT("%s  /  %s"),*P->Status,*P->LightName());
    DrawText(Info,Ink,X,Canvas->ClipY-70*S,GEngine->GetSmallFont(),S,false);
    DrawText(P->bFly?TEXT("FLIGHT   WASD + mouse   |   Q/E altitude   |   Shift faster"):TEXT("WALK   WASD + mouse   |   Shift faster   |   Space jump"),Muted,X,Canvas->ClipY-44*S,GEngine->GetSmallFont(),.95f*S,false);
    if(P->bHelp)
    {
        const float RX=Canvas->ClipX-338*S;
        DrawRect(FLinearColor(.017f,.028f,.03f,.74f),RX,Y,302*S,243*S);
        DrawText(TEXT("EXPLORE"),Gold,RX+20*S,Y+16*S,GEngine->GetSmallFont(),S,false);
        const TCHAR* Lines[]={TEXT("1    East canyon"),TEXT("2    Snake Path"),TEXT("3    South elevation"),TEXT("4    Aerial view"),TEXT("F    Walk / fly     L    Light"),TEXT("H    Clean view     P    Photo"),TEXT("Wheel    Zoom      Tab    Help"),TEXT("Esc    Exit")};
        for(int32 I=0;I<8;++I) DrawText(Lines[I],Ink,RX+20*S,Y+(48+23*I)*S,GEngine->GetSmallFont(),.9f*S,false);
    }
    else DrawText(TEXT("Tab  Help"),Muted,Canvas->ClipX-135*S,Y,GEngine->GetSmallFont(),S,false);
}
