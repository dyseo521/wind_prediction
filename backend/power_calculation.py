"""
전력 계산 모듈 - 풍력 및 지압 발전량 계산 기능을 제공합니다.
"""
import math
import numpy as np
from datetime import datetime, timedelta

class PowerCalculator:
    def __init__(self):
        # 풍력 발전기 설정
        self.wind_turbine_settings = {
            '5호관_60주년_사이': {
                'model': 'Lotus-V 1kW',
                'rated_power': 1000,  # Watts
                'start_wind_speed': 1.5,  # m/s
                'area': 3.14,  # m^2 (추정 단면적)
                'efficiency': 0.35,  # 효율 (35%)
                'count': 2  # 설치 개수
            },
            '인경호_앞': {
                'model': '미니 풍력 터빈 600W',
                'rated_power': 600,  # Watts
                'start_wind_speed': 1.2,  # m/s
                'area': 2.0,  # m^2 (추정 단면적)
                'efficiency': 0.30,  # 효율 (30%)
                'count': 3  # 설치 개수
            },
            '하이데거숲': {
                'model': 'Lotus-V 3kW',
                'rated_power': 3000,  # Watts
                'start_wind_speed': 1.5,  # m/s
                'area': 4.5,  # m^2 (추정 단면적)
                'efficiency': 0.40,  # 효율 (40%)
                'count': 1  # 설치 개수
            }
        }
        
        # 지압 발전기 설정
        self.piezo_tile_settings = {
            '5호관_60주년_사이': {
                'model': 'Pavegen',
                'power_per_step': 5,  # W (한 걸음당 평균 전력)
                'tiles_count': 275,   # 설치된 타일 수
                'avg_hourly_people': 754,  # 시간당 평균 인원
                'step_per_person': 4   # 한 사람당 평균 밟는 횟수
            },
            '인경호_앞': {
                'model': 'Pavegen',
                'power_per_step': 5,  # W
                'tiles_count': 200,   # 설치된 타일 수
                'avg_hourly_people': 562,  # 시간당 평균 인원
                'step_per_person': 4   # 한 사람당 평균 밟는 횟수
            },
            '하이데거숲': {
                'model': 'Pavegen',
                'power_per_step': 5,  # W
                'tiles_count': 230,   # 설치된 타일 수
                'avg_hourly_people': 616,  # 시간당 평균 인원
                'step_per_person': 4   # 한 사람당 평균 밟는 횟수
            }
        }
        
        # AC → DC 변환 효율
        self.ac_dc_efficiency = 0.70  # 70%
        
        # LED 가로등 전력 소비
        self.led_streetlight_power = 150  # W
        self.led_streetlight_hours = 12   # 하루 작동 시간
        
        # 지역별 가로등 개수
        self.streetlight_count = {
            '5호관_60주년_사이': 8,
            '인경호_앞': 9,
            '하이데거숲': 14
        }

    def calculate_wind_power(self, location, wind_speed, hours=1):
        """
        풍력 발전량 계산
        
        Args:
            location (str): 위치명 (5호관_60주년_사이, 인경호_앞, 하이데거숲)
            wind_speed (float): 풍속 (m/s)
            hours (float): 발전 시간 (시간 단위)
            
        Returns:
            float: 발전량 (Wh)
        """
        if location not in self.wind_turbine_settings:
            raise ValueError(f"지원되지 않는 위치: {location}")
            
        settings = self.wind_turbine_settings[location]
        
        # 시동 풍속 미만인 경우 발전량 없음
        if wind_speed < settings['start_wind_speed']:
            return 0.0
            
        # 공기 밀도 (kg/m^3)
        air_density = 1.225
        
        # 풍력 에너지 계산식: P = 0.5 * ρ * A * v^3 * η * t
        # ρ: 공기 밀도, A: 단면적, v: 풍속, η: 효율, t: 시간
        raw_power = 0.5 * air_density * settings['area'] * (wind_speed ** 3) * settings['efficiency']
        
        # 정격 출력 제한
        power = min(raw_power, settings['rated_power'])
        
        # 설치 개수 고려
        total_power = power * settings['count']
        
        # 시간을 곱해 에너지(Wh)로 변환
        energy = total_power * hours
        
        # AC → DC 변환 손실 적용 (그리드 연결 시)
        return energy * self.ac_dc_efficiency

    def calculate_piezo_power(self, location, people_count=None, hours=1):
        """
        지압 발전량 계산
        
        Args:
            location (str): 위치명 (5호관_60주년_사이, 인경호_앞, 하이데거숲)
            people_count (int, optional): 인원 수. None인 경우 위치별 평균값 사용
            hours (float): 발전 시간 (시간 단위)
            
        Returns:
            float: 발전량 (Wh)
        """
        if location not in self.piezo_tile_settings:
            raise ValueError(f"지원되지 않는 위치: {location}")
            
        settings = self.piezo_tile_settings[location]
        
        # 인원 수가 명시되지 않은 경우 위치별 평균값 사용
        if people_count is None:
            people_count = settings['avg_hourly_people'] * hours
        else:
            # 시간이 1이 아닌 경우 인원 수 조정
            if hours != 1:
                people_count = people_count * hours
        
        # 총 밟는 횟수 = 인원 수 * 한 사람당 평균 밟는 횟수
        total_steps = people_count * settings['step_per_person']
        
        # 발전량 계산: 총 밟는 횟수 * 한 걸음당 전력
        power = total_steps * settings['power_per_step']
        
        # 시간을 고려해 Wh 단위로 변환 (이미 hours를 인원 수에 반영했으므로 추가 곱셈 불필요)
        energy = power
        
        # AC → DC 변환 손실 적용
        return energy * self.ac_dc_efficiency

    def calculate_total_power(self, location, wind_speed, people_count=None, hours=1):
        """
        총 발전량 계산 (풍력 + 지압)
        
        Args:
            location (str): 위치명
            wind_speed (float): 풍속 (m/s)
            people_count (int, optional): 인원 수
            hours (float): 발전 시간
            
        Returns:
            dict: 발전량 정보 (풍력, 지압, 총합, 가로등 소비량, 잉여/부족량)
        """
        wind_power = self.calculate_wind_power(location, wind_speed, hours)
        piezo_power = self.calculate_piezo_power(location, people_count, hours)
        total_power = wind_power + piezo_power
        
        # 가로등 소비 전력
        streetlight_count = self.streetlight_count.get(location, 0)
        streetlight_consumption = self.led_streetlight_power * streetlight_count * min(hours, self.led_streetlight_hours)
        
        # 발전량과 소비량 차이
        power_balance = total_power - streetlight_consumption
        
        return {
            'location': location,
            'hours': hours,
            'wind_speed': wind_speed,
            'people_count': people_count if people_count is not None else self.piezo_tile_settings[location]['avg_hourly_people'] * hours,
            'wind_power_wh': round(wind_power, 2),
            'piezo_power_wh': round(piezo_power, 2),
            'total_power_wh': round(total_power, 2),
            'streetlight_consumption_wh': round(streetlight_consumption, 2),
            'power_balance_wh': round(power_balance, 2),
            'is_sufficient': power_balance >= 0,
            'sufficiency_percentage': round((total_power / max(0.1, streetlight_consumption)) * 100, 1) if streetlight_consumption > 0 else float('inf')
        }

    def predict_daily_power(self, location, hourly_wind_speeds, hourly_people_counts=None):
        """
        일일 발전량 예측
        
        Args:
            location (str): 위치명
            hourly_wind_speeds (list): 시간별 풍속 목록 (24개 요소)
            hourly_people_counts (list, optional): 시간별 인원 수 목록 (24개 요소)
            
        Returns:
            dict: 일일 발전량 정보
        """
        if len(hourly_wind_speeds) != 24:
            raise ValueError("시간별 풍속은 24개 요소를 가진 목록이어야 합니다.")
            
        if hourly_people_counts is not None and len(hourly_people_counts) != 24:
            raise ValueError("시간별 인원 수는 24개 요소를 가진 목록이어야 합니다.")
        
        daily_wind_power = 0
        daily_piezo_power = 0
        hourly_results = []
        
        for hour in range(24):
            wind_speed = hourly_wind_speeds[hour]
            
            people_count = None
            if hourly_people_counts is not None:
                people_count = hourly_people_counts[hour]
            
            # 시간별 발전량 계산
            result = self.calculate_total_power(location, wind_speed, people_count, 1)
            hourly_results.append(result)
            
            daily_wind_power += result['wind_power_wh']
            daily_piezo_power += result['piezo_power_wh']
        
        total_power = daily_wind_power + daily_piezo_power
        
        # 가로등 소비 전력 (12시간만 작동)
        streetlight_count = self.streetlight_count.get(location, 0)
        streetlight_consumption = self.led_streetlight_power * streetlight_count * self.led_streetlight_hours
        
        # 발전량과 소비량 차이
        power_balance = total_power - streetlight_consumption
        
        return {
            'location': location,
            'daily_wind_power_wh': round(daily_wind_power, 2),
            'daily_piezo_power_wh': round(daily_piezo_power, 2),
            'daily_total_power_wh': round(total_power, 2),
            'daily_total_power_kwh': round(total_power / 1000, 3),
            'streetlight_consumption_wh': round(streetlight_consumption, 2),
            'streetlight_consumption_kwh': round(streetlight_consumption / 1000, 3),
            'power_balance_wh': round(power_balance, 2),
            'power_balance_kwh': round(power_balance / 1000, 3),
            'is_sufficient': power_balance >= 0,
            'sufficiency_percentage': round((total_power / max(0.1, streetlight_consumption)) * 100, 1) if streetlight_consumption > 0 else float('inf'),
            'hourly_results': hourly_results
        }
        
    def predict_weekly_power(self, location, daily_wind_speeds, daily_people_multipliers=None):
        """
        주간 발전량 예측 (7일)
        
        Args:
            location (str): 위치명
            daily_wind_speeds (list): 일별 평균 풍속 목록 (7개 요소)
            daily_people_multipliers (list, optional): 일별 인원 수 배수 목록 (7개 요소)
                1.0은 평균 인원, 0.5는 평균의 50%, 2.0은 평균의 200%를 의미
            
        Returns:
            dict: 주간 발전량 정보
        """
        if len(daily_wind_speeds) != 7:
            raise ValueError("일별 풍속은 7개 요소를 가진 목록이어야 합니다.")
            
        if daily_people_multipliers is not None and len(daily_people_multipliers) != 7:
            raise ValueError("일별 인원 수 배수는 7개 요소를 가진 목록이어야 합니다.")
        
        # 기본 인원 수 배수 (모두 1.0, 주말에는 0.5로 설정)
        if daily_people_multipliers is None:
            # 월(0), 화(1), 수(2), 목(3), 금(4), 토(5), 일(6)
            daily_people_multipliers = [1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.3]
        
        weekly_wind_power = 0
        weekly_piezo_power = 0
        daily_results = []
        
        for day in range(7):
            wind_speed = daily_wind_speeds[day]
            people_multiplier = daily_people_multipliers[day]
            
            # 평균 시간당 인원 수
            avg_hourly_people = self.piezo_tile_settings[location]['avg_hourly_people']
            
            # 시간별 발전량을 기반으로 일일 발전량 계산
            # 간단한 모델: 낮 12시간은 설정된 풍속, 밤 12시간은 풍속의 80%
            hourly_wind_speeds = [wind_speed] * 12 + [wind_speed * 0.8] * 12
            
            # 인원 수 배수 적용: 8시간은 정상, 8시간은 절반, 8시간은 10%
            hourly_people_counts = []
            for h in range(24):
                if 8 <= h < 16:  # 주간 (8시-16시): 정상 인원
                    hourly_people_counts.append(int(avg_hourly_people * people_multiplier))
                elif 16 <= h < 24:  # 저녁 (16시-24시): 절반 인원
                    hourly_people_counts.append(int(avg_hourly_people * people_multiplier * 0.5))
                else:  # 새벽 (0시-8시): 10% 인원
                    hourly_people_counts.append(int(avg_hourly_people * people_multiplier * 0.1))
            
            daily_result = self.predict_daily_power(location, hourly_wind_speeds, hourly_people_counts)
            daily_results.append(daily_result)
            
            weekly_wind_power += daily_result['daily_wind_power_wh']
            weekly_piezo_power += daily_result['daily_piezo_power_wh']
        
        total_power = weekly_wind_power + weekly_piezo_power
        
        # 가로등 주간 소비 전력
        streetlight_count = self.streetlight_count.get(location, 0)
        streetlight_consumption = self.led_streetlight_power * streetlight_count * self.led_streetlight_hours * 7
        
        # 발전량과 소비량 차이
        power_balance = total_power - streetlight_consumption
        
        # 요일 이름 생성 (오늘이 첫 번째 날)
        today = datetime.now()
        day_names = [(today + timedelta(days=i)).strftime('%Y-%m-%d (%a)') for i in range(7)]
        
        for i, result in enumerate(daily_results):
            result['date'] = day_names[i]
        
        return {
            'location': location,
            'weekly_wind_power_wh': round(weekly_wind_power, 2),
            'weekly_wind_power_kwh': round(weekly_wind_power / 1000, 3),
            'weekly_piezo_power_wh': round(weekly_piezo_power, 2),
            'weekly_piezo_power_kwh': round(weekly_piezo_power / 1000, 3),
            'weekly_total_power_wh': round(total_power, 2),
            'weekly_total_power_kwh': round(total_power / 1000, 3),
            'streetlight_consumption_wh': round(streetlight_consumption, 2),
            'streetlight_consumption_kwh': round(streetlight_consumption / 1000, 3),
            'power_balance_wh': round(power_balance, 2),
            'power_balance_kwh': round(power_balance / 1000, 3),
            'is_sufficient': power_balance >= 0,
            'sufficiency_percentage': round((total_power / max(0.1, streetlight_consumption)) * 100, 1) if streetlight_consumption > 0 else float('inf'),
            'daily_results': daily_results
        }
    
    def predict_monthly_power(self, location, avg_wind_speed, monthly_temp_range=None, weekday_multiplier=1.0, weekend_multiplier=0.4):
        """
        월간 발전량 예측 (30일)
        
        Args:
            location (str): 위치명
            avg_wind_speed (float): 월 평균 풍속
            monthly_temp_range (tuple, optional): 월 최저/최고 온도 범위 (최저, 최고)
            weekday_multiplier (float): 평일 인원 수 배수
            weekend_multiplier (float): 주말 인원 수 배수
            
        Returns:
            dict: 월간 발전량 정보
        """
        # 현재 날짜로부터 30일간의 요일 패턴 생성
        today = datetime.now()
        is_weekend = [(today + timedelta(days=i)).weekday() >= 5 for i in range(30)]
        
        # 풍속 변동 생성 (기본 변동 ±20%)
        wind_variation = 0.2
        
        # 기온 범위에 따른 풍속 변동 추가
        if monthly_temp_range is not None:
            min_temp, max_temp = monthly_temp_range
            temp_range = max_temp - min_temp
            # 온도 범위가 크면 풍속 변동 증가 (최대 ±35%)
            wind_variation = min(0.35, 0.2 + (temp_range / 100))
        
        daily_wind_speeds = []
        daily_people_multipliers = []
        
        for day in range(30):
            # 풍속 변동 적용
            variation = np.random.uniform(-wind_variation, wind_variation)
            daily_wind_speed = avg_wind_speed * (1 + variation)
            daily_wind_speeds.append(max(0.5, daily_wind_speed))  # 최소 풍속 0.5m/s 보장
            
            # 인원 수 배수 (주말/평일)
            multiplier = weekend_multiplier if is_weekend[day] else weekday_multiplier
            daily_people_multipliers.append(multiplier)
        
        # 주간 단위로 계산 후 합산
        monthly_wind_power = 0
        monthly_piezo_power = 0
        weekly_results = []
        
        for week in range(4):  # 4주
            week_wind_speeds = daily_wind_speeds[week*7:(week+1)*7]
            week_people_multipliers = daily_people_multipliers[week*7:(week+1)*7]
            
            if len(week_wind_speeds) < 7:  # 마지막 주가 7일이 안되는 경우
                # 부족한 날짜 채우기
                week_wind_speeds = week_wind_speeds + [avg_wind_speed] * (7 - len(week_wind_speeds))
                week_people_multipliers = week_people_multipliers + [weekday_multiplier] * (7 - len(week_people_multipliers))
            
            weekly_result = self.predict_weekly_power(location, week_wind_speeds, week_people_multipliers)
            weekly_results.append(weekly_result)
            
            monthly_wind_power += weekly_result['weekly_wind_power_wh']
            monthly_piezo_power += weekly_result['weekly_piezo_power_wh']
        
        # 나머지 날짜 처리 (28일 이후)
        remaining_days = 30 - 28
        if remaining_days > 0:
            remaining_wind_speeds = daily_wind_speeds[28:]
            remaining_people_multipliers = daily_people_multipliers[28:]
            
            # 간단하게 나머지 일수 처리
            for i in range(remaining_days):
                daily_result = self.predict_daily_power(
                    location, 
                    [remaining_wind_speeds[i]] * 24,
                    [int(self.piezo_tile_settings[location]['avg_hourly_people'] * remaining_people_multipliers[i])] * 24
                )
                monthly_wind_power += daily_result['daily_wind_power_wh']
                monthly_piezo_power += daily_result['daily_piezo_power_wh']
        
        total_power = monthly_wind_power + monthly_piezo_power
        
        # 가로등 월간 소비 전력
        streetlight_count = self.streetlight_count.get(location, 0)
        streetlight_consumption = self.led_streetlight_power * streetlight_count * self.led_streetlight_hours * 30
        
        # 발전량과 소비량 차이
        power_balance = total_power - streetlight_consumption
        
        return {
            'location': location,
            'avg_wind_speed': avg_wind_speed,
            'days': 30,
            'monthly_wind_power_wh': round(monthly_wind_power, 2),
            'monthly_wind_power_kwh': round(monthly_wind_power / 1000, 3),
            'monthly_piezo_power_wh': round(monthly_piezo_power, 2),
            'monthly_piezo_power_kwh': round(monthly_piezo_power / 1000, 3),
            'monthly_total_power_wh': round(total_power, 2),
            'monthly_total_power_kwh': round(total_power / 1000, 3),
            'streetlight_consumption_wh': round(streetlight_consumption, 2),
            'streetlight_consumption_kwh': round(streetlight_consumption / 1000, 3),
            'power_balance_wh': round(power_balance, 2),
            'power_balance_kwh': round(power_balance / 1000, 3),
            'is_sufficient': power_balance >= 0,
            'sufficiency_percentage': round((total_power / max(0.1, streetlight_consumption)) * 100, 1) if streetlight_consumption > 0 else float('inf'),
            'weekly_results': weekly_results
        }
    
    def predict_annual_power(self, location, monthly_avg_wind_speeds, monthly_temp_ranges=None):
        """
        연간 발전량 예측 (12개월)
        
        Args:
            location (str): 위치명
            monthly_avg_wind_speeds (list): 월별 평균 풍속 목록 (12개 요소)
            monthly_temp_ranges (list, optional): 월별 온도 범위 목록 [(최저, 최고), ...]
            
        Returns:
            dict: 연간 발전량 정보
        """
        if len(monthly_avg_wind_speeds) != 12:
            raise ValueError("월별 풍속은 12개 요소를 가진 목록이어야 합니다.")
            
        if monthly_temp_ranges is not None and len(monthly_temp_ranges) != 12:
            raise ValueError("월별 온도 범위는 12개 요소를 가진 목록이어야 합니다.")
        
        # 월별 인원 수 배수 (학기 중/방학)
        # 학기: 3-6월, 9-12월은 정상, 방학: 1-2월, 7-8월은 50%
        monthly_people_multipliers = [0.5, 0.5, 1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 1.0, 1.0, 1.0, 1.0]
        
        annual_wind_power = 0
        annual_piezo_power = 0
        monthly_results = []
        
        for month in range(12):
            wind_speed = monthly_avg_wind_speeds[month]
            temp_range = None if monthly_temp_ranges is None else monthly_temp_ranges[month]
            people_multiplier = monthly_people_multipliers[month]
            
            # 주말 인원 가중치 (학기 중 주말은 40%, 방학 중 주말은 20%)
            weekend_multiplier = 0.4 if people_multiplier == 1.0 else 0.2
            
            monthly_result = self.predict_monthly_power(
                location, 
                wind_speed, 
                temp_range,
                people_multiplier,  # 평일 배수
                weekend_multiplier  # 주말 배수
            )
            
            monthly_results.append(monthly_result)
            
            annual_wind_power += monthly_result['monthly_wind_power_wh']
            annual_piezo_power += monthly_result['monthly_piezo_power_wh']
        
        total_power = annual_wind_power + annual_piezo_power
        
        # 가로등 연간 소비 전력 (365일)
        streetlight_count = self.streetlight_count.get(location, 0)
        streetlight_consumption = self.led_streetlight_power * streetlight_count * self.led_streetlight_hours * 365
        
        # 발전량과 소비량 차이
        power_balance = total_power - streetlight_consumption
        
        # 월 이름 설정
        month_names = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월']
        
        for i, result in enumerate(monthly_results):
            result['month'] = month_names[i]
        
        return {
            'location': location,
            'annual_wind_power_wh': round(annual_wind_power, 2),
            'annual_wind_power_kwh': round(annual_wind_power / 1000, 3),
            'annual_piezo_power_wh': round(annual_piezo_power, 2),
            'annual_piezo_power_kwh': round(annual_piezo_power / 1000, 3),
            'annual_total_power_wh': round(total_power, 2),
            'annual_total_power_kwh': round(total_power / 1000, 3),
            'streetlight_consumption_wh': round(streetlight_consumption, 2),
            'streetlight_consumption_kwh': round(streetlight_consumption / 1000, 3),
            'power_balance_wh': round(power_balance, 2),
            'power_balance_kwh': round(power_balance / 1000, 3),
            'is_sufficient': power_balance >= 0,
            'sufficiency_percentage': round((total_power / max(0.1, streetlight_consumption)) * 100, 1) if streetlight_consumption > 0 else float('inf'),
            'monthly_results': monthly_results
        }