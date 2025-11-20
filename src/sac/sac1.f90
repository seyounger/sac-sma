SUBROUTINE SAC1(DT, PXV, EP, TCI, ROIMP, SDRO, SSUR, SIF, BFS, BFP, TET, BFNCC, &
                IFRZE, TA, LWE, WE, ISC, AESC, &
                UZTWM, UZFWM, UZK, PCTIM, ADIMP, RIVA, ZPERC, &
                REXP, LZTWM, LZFSM, LZFPM, LZSK, LZPK, PFREE, SIDE, RSERV, &
                UZTWC, UZFWC, LZTWC, LZFSC, LZFPC, ADIMC)
  
  ! Use the module ONLY for global/summation arrays (FGCO, RSUM, FSUMS1, etc.)
  USE sac_data_mod, ONLY: dp, FGPM, FGCO, RSUM, PPE, PSC, PTA, PWE, &
                          SROT, SIMPVT, SRODT, SROST, SINTFT, SGWFP, SGWFS, SRECHT, &
                          SETT, SE1, SE2, SE3, SE4, SE5
  
IMPLICIT NONE
  
  ! ----- DUMMY ARGUMENTS (Passed In/Out) -----
  DOUBLE PRECISION, INTENT(IN)    :: DT, PXV, EP
  DOUBLE PRECISION, INTENT(IN)    :: TA, LWE, WE, AESC
  INTEGER, INTENT(IN)     :: IFRZE, ISC
  DOUBLE PRECISION, INTENT(INOUT) :: TCI, ROIMP, SDRO, SSUR, SIF, BFS, BFP, TET, BFNCC

  ! SAC Parameters (IN)
  DOUBLE PRECISION, INTENT(IN)    :: UZTWM, UZFWM, UZK, PCTIM, ADIMP, RIVA, ZPERC, &
                             REXP, LZTWM, LZFSM, LZFPM, LZSK, LZPK, PFREE, &
                             SIDE, RSERV
                             
  ! SAC State Variables (INOUT - Their values change here)
  DOUBLE PRECISION, INTENT(INOUT) :: UZTWC, UZFWC, LZTWC, LZFSC, LZFPC, ADIMC
  
  ! ----- LOCAL VARIABLES (All converted to DOUBLE PRECISION) -----
  DOUBLE PRECISION :: EDMND, E1, RED, E2, UZRAT, E3, RATLZT, SAVED, RATLZ, DEL, E5
  DOUBLE PRECISION :: TWX, SPERC, DINC, PINC, DUZ, DLZP, DLZS, PAREA, ADSUR, RATIO, ADDRO
  DOUBLE PRECISION :: BF, SBF, SPBF, PERCM, PERC, DEFR, FR, FI, UZDEFR, CHECK, PERCT, PERCF
  DOUBLE PRECISION :: HPL, RATLP, RATLS, FRACP, PERCP, PERCS, EXCESS, SUR, EUSED, TBF, BFCC, E4
  DOUBLE PRECISION :: FRACP_DENOM
  INTEGER  :: I, NINC
  LOGICAL  :: bypass_ratio_check = .FALSE. ! <-- NEW FLAG TO FIX GOTO equivalents
  DOUBLE PRECISION :: THRES_ZERO
  DOUBLE PRECISION :: SURF_REMAINDER

  ! Threshold to be considered as zero
  THRES_ZERO = 0.000000001_dp
  PAREA = 1.0_dp - ADIMP - PCTIM
  

  ! Set potential evapotranspiration
  EDMND = EP
  ! Compute ET1 FROM Upper zone tension water storage
  E1 = EDMND * UZTWC / UZTWM
  ! Residual ET demand
  RED = EDMND - E1
  UZTWC = UZTWC - E1
  ! ET2 from upper zone free water storage
  E2 = 0.0_dp

  ! In case ET1 > UZTWS, no water in the upper
  ! tension water storage
  !!! This IF/ELSE logic here differs from   !!!!
  !!!! NOAA-OWP/sac-sma in which this R I    !!!!
  !!!! IF/ELSE statement had to be met with  !!!!
  !!!! UZWTC <= 0.0; NOAA-OWP/sac-sma        !!!!
  !!!! critera was UZWTC < 0.0               !!!!  
  IF (UZTWC .LE. 0.0_dp) THEN
    E1 = E1 + UZTWC
    UZTWC = 0.0_dp
    RED = EDMND - E1
    
    ! When upper zone free water content is less than
    ! residual ET
    IF (UZFWC .LT. RED) THEN
      ! All content at upper zone free water zone will
      ! be gone as ET
      E2 = UZFWC
      UZFWC = 0.0_dp
      RED = RED - E2
      !!!! New implementation in R Code that   !!!!
      !!!! was not present in NOAA-OWP/sac-sma !!!!
      IF (UZTWC < THRES_ZERO) UZTWC = 0.0_dp
      IF (UZFWC < THRES_ZERO) UZFWC = 0.0_dp
    ELSE
      ! When upper zone free water content is more than 
      ! residual ET
      E2 = RED ! all residual ET will be gone as ET
      UZFWC = UZFWC - E2
      RED = 0.0_dp
    END IF
  !!!! This IF/ELSE logic here differs from   !!!!
  !!!! NOAA-OWP/sac-sma in which this ELSE    !!!!
  !!!! statement had to be met only with      !!!!
  !!!! UZWTC < 0.0; NOAA-OWP/sac-sma critera !!!!
  !!!! was UZWTC <= 0.0 OR                    !!!!
  !!!! UTZWC < 0.0 and UZFWC >= RED.          !!!!
  
  ! In the case ET1 <= UZTWS, all maximum et (et1) are
  ! consumed at UZTWC, so no et from uzfwc (et2=0)
  ELSE  
    ! There's possibility that upper zone free water ratio exceeds
    ! upper zone tension water ratio. If so, free water is
    ! transferred to tension water storage
    IF ((UZTWC / UZTWM) .LT. (UZFWC / UZFWM)) THEN
      UZRAT = (UZTWC + UZFWC) / (UZTWM + UZFWM)
      UZTWC = UZTWM * UZRAT
      UZFWC = UZFWM * UZRAT
    END IF
    !!!! New implementation in R Code that   !!!!
    !!!! was not present in NOAA-OWP/sac-sma !!!!    
    IF (UZTWC < THRES_ZERO) UZTWC = 0.0_dp
    IF (UZFWC < THRES_ZERO) UZFWC = 0.0_dp
  END IF

  ! ET(3), ET from Lower zone tension water storage when
  ! residual ET > 0
  ! residual ET is always bigger than ET(3)
  E3 = RED * LZTWC / (UZTWM + LZTWM)
  LZTWC = LZTWC - E3

  ! If lztwc is less than zero, et3 cannot exceed lztws
  IF (LZTWC .LT. 0.0_dp) THEN
    E3 = E3 + LZTWC
    LZTWC = 0.0_dp
  END IF

  ! Water resupply from Lower free water storages to
  ! Lower tension water storage
  SAVED = RSERV * (LZFPM + LZFSM)  
  RATLZT = LZTWC / LZTWM
  RATLZ = (LZTWC + LZFPC + LZFSC - SAVED) / (LZTWM + LZFPM + LZFSM - SAVED)

  ! Water is first taken from supplementary water 
  ! storage for resupply
  IF (RATLZT .LT. RATLZ) THEN
    DEL = (RATLZ - RATLZT) * LZTWM
    LZTWC = LZTWC + DEL ! Transfer water from lzfss to lztws
    LZFSC = LZFSC - DEL

    ! If tranfer exceeds lzfsc then remainder comes from lzfps
    IF (LZFSC .LT. 0.0_dp) THEN
      LZFPC = LZFPC + LZFSC
      LZFSC = 0.0_dp
    END IF
  END IF

  IF (LZTWC < THRES_ZERO) LZTWC = 0.0_dp

  ! ET(5), ET from additional impervious (ADIMP) area
  ! ????? no idea where this come from, I think there's
  ! a possibility that et5 can be negative values
  E5 = E1 + (RED + E2) * (ADIMC - E1 - UZTWC) / (UZTWM + LZTWM)
  ADIMC = ADIMC - E5
  
  IF (ADIMC .LT. 0.0_dp) THEN
    ! et5 cannot exceed adims
    E5 = E5 + ADIMC
    ADIMC = 0.0_dp
  END IF
  E5 = E5 * ADIMP

  ! Time interval available moisture in excess of uztw requirements
  TWX = PXV + UZTWC - UZTWM

  ! All moisture held in uztw- no excess
  IF (TWX .LT. 0.0_dp) THEN
    UZTWC = UZTWC + PXV
    TWX = 0.0_dp
  ! Moisture available in excess of uztw storage
  ELSE
    UZTWC = UZTWM
  END IF

  ! For now twx is excess rainfall after filling the uztwc
  ADIMC = ADIMC + PXV - TWX
  
  ! Compute Impervious Area Runoff
  ROIMP = PXV * PCTIM
  
  ! Initialize time interval sums
  SBF=0.0_dp; SSUR=0.0_dp; SIF=0.0_dp; SPERC=0.0_dp; SDRO=0.0_dp; SPBF=0.0_dp

  ! Determine computational time increments for the basic time interval

  ! Number of time increments that interval is divided 
  ! into for further soil-moisture accountng
  NINC = INT(FLOOR(1.0_dp + 0.2_dp * (UZFWC + TWX)))
  IF (NINC .LT. 1) NINC = 1

  ! Length of each increment in days
  DINC = (1.0_dp / REAL(NINC, dp)) * DT
  ! Amount of available moisture for each increment
  PINC = TWX / REAL(NINC, dp)

  ! Compute free water depletion fractions for the time increment 
  ! (basic depletions are for one day)
  DUZ = 1.0_dp - ((1.0_dp - UZK) ** DINC)
  DLZP = 1.0_dp - ((1.0_dp - LZPK) ** DINC)
  DLZS = 1.0_dp - ((1.0_dp - LZSK) ** DINC)
  
  ! Start incremental for-loop for the time interval
  DO I = 1, NINC
    ! Amount of surface runoff. This will be updated.
    ADSUR = 0.0_dp

    ! Compute direct runoff from adimp area
    RATIO = (ADIMC - UZTWC) / LZTWM
    IF (RATIO .LT. 0.0_dp) RATIO = 0.0_dp

    ! Amount of direct runoff from the additional impervious area 
    ADDRO = PINC * (RATIO ** 2)
    
    ! Compute baseflow and keep track of time interval sum
    ! Baseflow from free water primary storage
    BF = LZFPC * DLZP
    LZFPC = LZFPC - BF
    IF (LZFPC .LE. 0.0001_dp) THEN
      BF = BF + LZFPC
      LZFPC = 0.0_dp
    END IF
    
    SBF = SBF + BF
    SPBF = SPBF + BF

    ! Baseflow from free water supplemental storage
    BF = LZFSC * DLZS
    LZFSC = LZFSC - BF
    IF (LZFSC .LE. 0.0001_dp) THEN
      BF = BF + LZFSC
      LZFSC = 0.0_dp
    END IF

    ! Total Baseflow from primary and supplemental storages
    SBF = SBF + BF
    
    ! Compute PERCOLATION- if no water available then skip.
    IF ((PINC + UZFWC) .LE. 0.01_dp) THEN
      UZFWC = UZFWC + PINC
    ELSE
      ! Limiting drainage rate from the combined saturated
      ! lower zone storages
      PERCM = LZFPM * DLZP + LZFSM * DLZS
      PERC = PERCM * (UZFWC / UZFWM)

      ! DEFR is the lower zone moisture deficiency ratio
      DEFR = 1.0_dp - (LZTWC + LZFPC + LZFSC) / (LZTWM + LZFPM + LZFSM)

      !!!! New implementation in R Code that   !!!!
      !!!! was not present in NOAA-OWP/sac-sma !!!!
      IF (DEFR .LT. 0.0_dp) DEFR = 0.0_dp

      !!!!!!!! Not in R code, but kept to potentially  !!!!!!!!!!!!!!!
      !!!!!!!! allow frozen ground implementation in the future !!!!!!
      FR = 1.0_dp
      FI = 1.0_dp

      ! Frozen Ground Adjustment
      IF (IFRZE .NE. 0) THEN
        UZDEFR = 1.0_dp - ((UZTWC + UZFWC) / (UZTWM + UZFWM))
        CALL FGFR1(DEFR, FR, FI, LZTWC, LZFSC, LZFPC, LZTWM, LZFPM, LZFSM)
      END IF
      !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

      
      PERC = PERC * (1.0_dp + ZPERC * (DEFR ** REXP)) * FR

      ! Note. . . percolation occurs from uzfws before pav is added

      ! Percolation rate exceeds uzfws
      IF (PERC .GE. UZFWC) THEN
        PERC = UZFWC
      END IF 

      ! Percolation rate is less than uzfws.
      UZFWC = UZFWC - PERC

      ! Check to see if percolation exceeds lower zone deficiency.
      CHECK = LZTWC + LZFPC + LZFSC + PERC - LZTWM - LZFPM - LZFSM
      IF (CHECK .GT. 0.0_dp) THEN
        PERC = PERC - CHECK
        UZFWC = UZFWC + CHECK
      END IF

      ! SPERC is the time interval summation of PERC
      SPERC = SPERC + PERC
      
      ! Compute interflow and keep track of time interval sum. 
      ! Note that PINC has not yet been added.
      DEL = UZFWC * DUZ * FI
      SIF = SIF + DEL
      UZFWC = UZFWC - DEL
     
      ! Distribute percolated water into the lower zones. Tension water
      ! must be filled first except for the PFREE area. PERCT is
      ! percolation to tension water and PERCF is percolation going to
      ! free water.
      
      ! Percolation going to the tension water storage
      PERCT = PERC * (1.0_dp - PFREE)
      
      IF ((PERCT + LZTWC) .LE. LZTWM) THEN
        LZTWC = LZTWC + PERCT
        ! Pecolation going to th lower zone free water storages
        PERCF = 0.0_dp      
      ELSE
        PERCF = PERCT + LZTWC - LZTWM
        LZTWC = LZTWM
      END IF 

      ! Distribute percolation in excess of tension requirements
      ! among the free water storages.
      PERCF = PERCF + (PERC * PFREE)
      
      IF (PERCF .NE. 0.0_dp) THEN
        ! Relative size of the primary storage as compared with
        ! total lower zone free water storages
        HPL = LZFPM / (LZFPM + LZFSM)
        ! Relative fullness of each storage.
        RATLP = LZFPC / LZFPM
        RATLS = LZFSC / LZFSM
        ! The fraction going to primary
        FRACP = HPL * 2.0_dp * (1.0_dp - RATLP) / (2.0_dp - ratlp - ratls)
        IF (FRACP .GT. 1.0_dp) FRACP = 1.0_dp
        ! Amount of the excess percolation going to primary      
        PERCP = PERCF * FRACP
        ! Amount of the excess percolation going to supplemental
        PERCS = PERCF - PERCP
        LZFSC = LZFSC + PERCS
        
        IF (LZFSC .GT. LZFSM) THEN
          PERCS = PERCS - LZFSC + LZFSM
          LZFSC = LZFSM
        END IF 
        
        LZFPC = LZFPC + PERCF - PERCS

      !!!! New implementation in R Code that   !!!!
      !!!! was not present in NOAA-OWP/sac-sma !!!!
      !!!! which was originally the IF logic   !!!!
      !!!! of LZFPC .GT. LZFPM                 !!!!
        ! Check to make sure lzfps does not exceed lzfpm
        IF (LZFPC .GE. LZFPM) THEN
          EXCESS = LZFPC - LZFPM
          LZTWC = LZTWC + EXCESS
          LZFPC = LZFPM
        END IF
        
      END IF
      
      ! Distribute PINC between uzfws and surface runoff
      IF (PINC .NE. 0.0_dp) THEN

        ! Check if pinc exceeds uzfwm
        IF ((PINC + UZFWC) .LE. UZFWM) THEN
        ! no surface runoff
        UZFWC = UZFWC + PINC
        ELSE
          ! Surface runoff
          SUR = PINC + UZFWC - UZFWM
          UZFWC = UZFWM
          SSUR = SSUR + (SUR * PAREA)
          ! ADSUR is the amount of surface runoff which comes from
          ! that portion of adimp which is not currently generating
          ! direct runoff. ADDRO/PINC is the fraction of adimp
          ! currently generating direct runoff.
          ADSUR = SUR * (1.0_dp - ADDRO / PINC)
          SSUR = SSUR + ADSUR * ADIMP          
        END IF
      END IF
      
    END IF
      
      ! ADIMP Area Water Balance
      ADIMC = ADIMC + PINC - ADDRO - ADSUR
      
      IF (ADIMC .GT. (UZTWM + LZTWM)) THEN
        ADDRO = ADDRO + ADIMC - (UZTWM + LZTWM)
        ADIMC = UZTWM + LZTWM
      END IF 

      ! Direct runoff from the additional impervious area
      SDRO = SDRO + ADDRO * ADIMP

      !!!! New implementation in R Code that   !!!!
      !!!! was not present in NOAA-OWP/sac-sma !!!!
      IF(ADIMC < THRES_ZERO) ADIMC = 0.0_dp
      
  ! END of incremental for loop     
  END DO

  ! Compute sums and adjust runoff amounts by 
  ! the area over which they are generated.

  ! EUSED is the ET from PAREA which is 1.0 - adimp - pctim
  EUSED = E1 + E2 + E3
  SIF = SIF * PAREA

  ! Separate channel component of baseflow from the non-channel component
  TBF = SBF * PAREA ! TBF is the total baseflow
  BFCC = TBF / (1.0_dp + SIDE) ! BFCC is baseflow, channel component 

  
  !!!!!!!! Not in R code, but same calculations for  !!!!!!!!!!
  !!!!!!!! sac-sma output needed for the BMI that is !!!!!!!!!!
  !!!!!!!! essentially output in the R code base     !!!!!!!!!!
  BFP = SPBF * PAREA / (1.0_dp + SIDE)
  BFS = BFCC - BFP
  IF (BFS .LT. 0.0_dp) BFS = 0.0_dp
  BFNCC = TBF - BFCC
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


  !  Surface flow consists of Direct runoff and Surface inflow to the channel
  TCI = ROIMP + SDRO + SSUR + SIF + BFCC

  ! ET(4)- ET from riparian vegetation.
  ! No effect if riva is set to zero
  E4 = (EDMND - EUSED) * RIVA


  ! Check that adims >= uztws
  IF (ADIMC .LT. UZTWC) ADIMC = UZTWC 

  ! If there is no channel inflow due to 
  ! direct runoff and surface inflow to 
  ! the channel, but ET from riparian vegetation
  ! is present, then to balance the mass
  ! out in the system, we must cancel out 
  ! the  ET from riparian vegetation
  IF(TCI > E4) THEN
    ! Total inflow to channel for a timestep
    TCI = TCI - E4
  ELSE
    ! If TCI become negative because
    ! of ET from riparian vegetation
    ! being larger, than we offset
    ! ET from riparian vegetation
    ! with the TCI term and then
    ! set TCI to zero to balance
    ! out mass in the system
    E4 = TCI
    TCI = 0.0_dp
  ENDIF


  ! Compute total evapotransporation - TET
  EUSED = EUSED * PAREA
  TET = EUSED + E5 + E4

  
  !!! This R code flag here causes mass imbalance to explode !!!!
  !!! TCI is a component to mass balance, which should be allowed !!!
  !!! to be negative to indicate a balance between mass gained !!!
  !!! and mass lost within the given system !!!
  !IF (TCI .LT. 0.0_dp) THEN
  !  BFCC = 0.0_dp
  !  TCI = 0.0_dp
  !ELSE
  !   SURF_REMAINDER = ROIMP + SDRO + SSUR + SIF - E4
  !   TCI = MAX(0.0_dp,SURF_REMAINDER)
  !   ! In this case, base is reduced
  !   IF (SURF_REMAINDER < 0.0_dp) THEN
  !     BFCC = BFCC + SURF_REMAINDER
  !     IF (BFCC < 0.0_dp) BFCC = 0.0_dp
  !   ENDIF
  !END IF
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


  !!!!!!!! Not in R code, but kept to potentially  !!!!!!!!!!!!!!!
  !!!!!!!! allow frozen ground implementation in the future !!!!!!


  ! Call FROST1 Subroutine
  IF (IFRZE .GT. 0) CALL FROST1(PXV, SSUR, SDRO, TA, LWE, WE, ISC, AESC, DT, &
                               UZTWM, UZFWM, LZTWM, LZFSM, LZFPM, LZSK, LZPK, &
                               UZTWC, UZFWC, LZTWC, LZFSC, LZFPC)

  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  
  
END SUBROUTINE SAC1



! ====================================================================
! SUBROUTINE FGFR1 - FROZEN GROUND ADJUSTMENTS
! ====================================================================

SUBROUTINE FGFR1(LZDEFR, FR, FI, LZTWC, LZFSC, LZFPC, LZTWM, LZFPM, LZFSM)
  ! THIS SUBROUTINE COMPUTES THE CHANGE IN THE PERCOLATION AND
  ! INTERFLOW WITHDRAWAL RATES DUE TO FROZEN GROUND.

  ! WRITTEN BY -- ERIC ANDERSON - HRL   JUNE 1980
  
  USE sac_data_mod, ONLY: dp, FGCO, FGPM

  IMPLICIT NONE

  ! ----- DUMMY ARGUMENTS -----
  DOUBLE PRECISION, INTENT(IN)    :: LZDEFR
  DOUBLE PRECISION, INTENT(INOUT) :: FR, FI
  DOUBLE PRECISION, INTENT(IN)    :: LZTWC, LZFSC, LZFPC, LZTWM, LZFPM, LZFSM

  ! ----- LOCAL VARIABLES -----
  DOUBLE PRECISION :: FINDX, FRTEMP, SATR, FREXP, EXP, FSAT, FDRY

  ! INITIAL VALUES (FGCO, FGPM are global)
  FINDX = FGCO(1)
  FRTEMP = FGPM(5)
  SATR = FGPM(6)
  FREXP = FGPM(7)


  ! DETERMINE IF FROZEN GROUND EFFECT EXISTS.
  IF (FINDX .LT. FRTEMP) THEN
    ! COMPUTE SATURATED REDUCTION.
    EXP = FRTEMP - FINDX
    FSAT = (1.0_dp - SATR) ** EXP
    ! CHANGE AT DRY CONDITIONS
    FDRY = 1.0_dp
    ! COMPUTE ACTUAL CHANGE
    IF (LZDEFR .GT. 0.0_dp) THEN
      FR = FSAT + (FDRY - FSAT) * (LZDEFR ** FREXP)
      FI = FR
      RETURN
    ELSE
      FR = FSAT
      FI = FR
      RETURN
    END IF
  ELSE
    RETURN
  ENDIF
  
END SUBROUTINE FGFR1


! ====================================================================
! SUBROUTINE FROST1 - FROZEN GROUND INDEX UPDATE
! ====================================================================

SUBROUTINE FROST1(PX, SUR, DIR, TA, LWE, WE, ISC, AESC, DT, &
                  UZTWM, UZFWM, LZTWM, LZFSM, LZFPM, LZSK, LZPK, &
                  UZTWC, UZFWC, LZTWC, LZFSC, LZFPC)
  ! THIS SUBROUTINE COMPUTES THE CHANGE IN THE FROZEN GROUND
  ! INDEX AND MOISTURE MOVEMENT DUE TO TEMPERATURE GRADIENTS.

  ! WRITTEN BY ERIC ANDERSON - HRL   JUNE 1980

  USE sac_data_mod, ONLY: dp, FGPM, FGCO

  IMPLICIT NONE

  ! ----- DUMMY ARGUMENTS -----
  DOUBLE PRECISION, INTENT(IN)    :: PX, SUR, DIR, TA, LWE, WE, AESC, DT
  INTEGER, INTENT(IN)     :: ISC

  ! SAC Parameters (IN)
  DOUBLE PRECISION, INTENT(IN)    :: UZTWM, UZFWM, LZTWM, LZFSM, LZFPM, LZSK, LZPK

  ! SAC State Variables (INOUT)
  DOUBLE PRECISION, INTENT(INOUT) :: UZTWC, UZFWC, LZTWC, LZFSC, LZFPC

  ! ----- LOCAL VARIABLES -----
  DOUBLE PRECISION :: FINDX, FINDX1, CSOIL, CSNOW, GHC, RTHAW, WATER, COVER, TWE, C, CFI

  ! INITIAL VALUES (FGCO, FGPM are global)
  FINDX = FGCO(1)
  FINDX1 = FINDX
  CSOIL = 4.0_dp * DT * FGPM(1)
  CSNOW = FGPM(2)
  GHC = FGPM(3) * DT
  RTHAW = FGPM(4)

  ! COMPUTE MOISTURE MOVEMENT
  ! EQUATIONS NOT READY YET.

! COMPUTE CHANGE IN FROZEN GROUND INDEX.
  ! CHANGE DUE TO WATER FREZING IN THE SOIL.
  IF (FINDX .LT. 0.0_dp) THEN
    WATER = PX - SUR - DIR
    IF (WATER .GT. 0.0_dp) THEN
      FINDX = FINDX + RTHAW * WATER
      IF (FINDX .GT. 0.0_dp) FINDX = 0.0_dp
    END IF
  END IF

  ! CHANGE DUE TO TEMPERATURE.
  IF ((FINDX .GE. 0.0_dp) .AND. (TA .GE. 0.0_dp)) THEN
    IF (FINDX.LT.0.0_dp) THEN
      CONTINUE
    ELSE
      FINDX=0.0_dp
      FGCO(1)=FINDX
      RETURN
    ENDIF
  ENDIF

  ! COMPUTE TRANSFER COEFFIENT.
  
  IF (LWE .EQ. 0.0_dp) THEN
    C = CSOIL
    ! COMPUTE CHANGE IN FROST INDEX.
    IF (TA.GE.0.0_dp) THEN
      FINDX=FINDX+C*TA+GHC
      ! CHECK FROST INDEX
      IF (FINDX.LT.0.0_dp) THEN
        CONTINUE
      ELSE
        FINDX = 0.0_dp
        ! SAVE NEW FROST INDEX
        FGCO(1)=FINDX
        RETURN
      ENDIF
    ENDIF
  ENDIF

  ! COMPUTE TRANSFER COEFFIENT.
  IF (WE .EQ. 0.0_dp) THEN
    C = CSOIL
    ! COMPUTE CHANGE IN FROST INDEX.
    IF (TA.GE.0.0_dp) THEN
      FINDX=FINDX+C*TA+GHC
      ! CHECK FROST INDEX
      IF (FINDX.LT.0.0_dp) THEN
        CONTINUE
      ELSE
        FINDX = 0.0_dp
        ! SAVE NEW FROST INDEX
        FGCO(1)=FINDX
        RETURN
      ENDIF
    ENDIF
  ENDIF

IF (ISC.GT.0.0_dp) THEN
  COVER=AESC
  IF (COVER.EQ.0.0_dp) THEN
    C=CSOIL
    IF (TA.GE.0.0_dp) THEN
      FINDX=FINDX+C*TA+GHC
      IF (FINDX.LT.0.0_dp) THEN
        CONTINUE
      ELSE
        FINDX = 0.0_dp
        ! SAVE NEW FROST INDEX
        FGCO(1)=FINDX
        RETURN
      ENDIF
    ELSE
      CFI=-C*SQRT(TA*TA+FINDX*FINDX)-C*FINDX+GHC
      FINDX=FINDX+CFI
      IF (FINDX.LT.0.0_dp) THEN
        CONTINUE
      ELSE
        FINDX = 0.0_dp
        ! SAVE NEW FROST INDEX
        FGCO(1)=FINDX
        RETURN
      ENDIF
    ENDIF
  ELSE
    TWE=WE/COVER
    C=CSOIL*(1.0_dp-COVER)+CSOIL*((1.0_dp-CSNOW)**TWE)*COVER
    IF (TA.GE.0.0_dp) THEN
      FINDX=FINDX+C*TA+GHC
      IF (FINDX.LT.0.0_dp) THEN
        CONTINUE
      ELSE
        FINDX = 0.0_dp
        ! SAVE NEW FROST INDEX
        FGCO(1)=FINDX
        RETURN
      ENDIF
    ELSE
      CFI=-C*SQRT(TA*TA+FINDX*FINDX)-C*FINDX+GHC
      FINDX=FINDX+CFI
      IF (FINDX.LT.0.0_dp) THEN
        CONTINUE
      ELSE
        FINDX = 0.0_dp
        ! SAVE NEW FROST INDEX
        FGCO(1)=FINDX
        RETURN
      ENDIF
    ENDIF    
  ENDIF
ELSE
  COVER=1.0_dp
  TWE=WE/COVER
  C=CSOIL*(1.0_dp-COVER)+CSOIL*((1.0_dp-CSNOW)**TWE)*COVER
  IF (TA.GE.0.0_dp) THEN
    FINDX=FINDX+C*TA+GHC
    IF (FINDX.LT.0.0_dp) THEN
      CONTINUE
    ELSE
      FINDX = 0.0_dp
      ! SAVE NEW FROST INDEX
      FGCO(1)=FINDX
      RETURN
    ENDIF
  ELSE
    CFI=-C*SQRT(TA*TA+FINDX*FINDX)-C*FINDX+GHC
    FINDX=FINDX+CFI
    IF (FINDX.LT.0.0_dp) THEN
      CONTINUE
    ELSE
      FINDX = 0.0_dp
      ! SAVE NEW FROST INDEX
      FGCO(1)=FINDX
      RETURN
    ENDIF
  ENDIF    
ENDIF

COVER=1.0_dp
TWE=WE/COVER
C=CSOIL*(1.0_dp-COVER)+CSOIL*((1.0_dp-CSNOW)**TWE)*COVER
IF (TA.GE.0.0_dp) THEN
  FINDX=FINDX+C*TA+GHC
  IF (FINDX.LT.0.0_dp) THEN
    CONTINUE
  ELSE
    FINDX = 0.0_dp
    ! SAVE NEW FROST INDEX
    FGCO(1)=FINDX
    RETURN
  ENDIF
ELSE
  CFI=-C*SQRT(TA*TA+FINDX*FINDX)-C*FINDX+GHC
  FINDX=FINDX+CFI
  IF (FINDX.LT.0.0_dp) THEN
    CONTINUE
  ELSE
    FINDX = 0.0_dp
    ! SAVE NEW FROST INDEX
    FGCO(1)=FINDX
    RETURN
  ENDIF
ENDIF    
 
END SUBROUTINE FROST1
