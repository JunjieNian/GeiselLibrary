#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/HUD.h"
#include "GeiselExperience.generated.h"

class UCameraComponent;
UCLASS()
class GEISELEXPLORER_API AGeiselCharacter : public ACharacter
{
    GENERATED_BODY()
public:
    AGeiselCharacter();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    UPROPERTY(VisibleAnywhere) UCameraComponent* Camera;
    bool bPhoto = false;
    bool bHelp = true;
    bool bFly = true;
    int32 LightPreset = 0;
    int32 ViewIndex = 0;
    FString Status = TEXT("EAST CANYON");
    FString LightName() const;
private:
    void Forward(float V); void Right(float V); void Rise(float V);
    void Yaw(float V); void Pitch(float V); void Zoom(float V);
    void Fast(); void Slow(); void Mode(); void Light(); void Photo(); void Help();
    void View1(); void View2(); void View3(); void View4(); void Shot(); void Exit(); void Hop();
    void ApplyLight(); void SetView(int32 Index); bool SetWalking();
    void SelfTest(float DeltaSeconds); void Capture(const FString& Name);
    bool bTest = false;
    bool bTestFailed = false;
    int32 TestPhase = 0;
    float TestTime = 0;
    FVector TestLocation = FVector::ZeroVector;
    FVector WalkLocation = FVector::ZeroVector;
    FVector TestMoveDirection = FVector::ForwardVector;
    void Check(bool Passed, const TCHAR* Name, const FString& Detail = FString());
};

UCLASS()
class GEISELEXPLORER_API AGeiselHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
};

UCLASS()
class GEISELEXPLORER_API AGeiselGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AGeiselGameMode();
};
