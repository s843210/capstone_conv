import React from 'react';
import {SafeAreaView, View, Text, Pressable} from 'react-native';
import {StartScreenProps} from '../types';
import {styles} from '../styles/commonStyles';

export default function StartScreen({navigation}: StartScreenProps) {
  return (
    <SafeAreaView style={styles.page}>
      <View style={styles.heroCard}>
        <Text style={styles.badge}>교내 편의점</Text>
        <Text style={styles.heroTitle}>교내 편의점 상품 요청 앱</Text>
        <Text style={styles.heroDesc}>
          편의점 상품의 재고를 확인하고, 필요한 수량을 간편하게 요청할 수 있는 서비스입니다.
        </Text>
        <Pressable style={styles.primaryBtn} onPress={() => navigation.navigate('Login')}>
          <Text style={styles.primaryBtnText}>시작하기</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}
