import React, {useState} from 'react';
import {SafeAreaView, Text, TextInput, Pressable, Alert} from 'react-native';
import {LoginScreenProps} from '../types';
import {styles} from '../styles/commonStyles';

type Props = LoginScreenProps & {
  loginUser: (name: string) => Promise<boolean>;
};

export default function LoginScreen({navigation, loginUser}: Props) {
  const [name, setName] = useState('');

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>간단 로그인</Text>
      <TextInput
        placeholder="이름 또는 학번 입력"
        value={name}
        onChangeText={setName}
        style={styles.input}
      />
      <Pressable
        style={styles.primaryBtn}
        onPress={async () => {
          const trimmedName = name.trim();
          if (!trimmedName) {
            Alert.alert('입력 필요', '이름 또는 학번을 입력해 주세요.');
            return;
          }
          if (trimmedName.length < 2) {
            Alert.alert('입력 오류', '이름 또는 학번을 2자 이상 입력해 주세요.');
            return;
          }

          const saved = await loginUser(trimmedName);
          if (!saved) {
            Alert.alert('로그인 오류', '사용자 정보를 저장하지 못했습니다. 다시 시도해 주세요.');
            return;
          }

          navigation.replace('ProductList');
        }}>
        <Text style={styles.primaryBtnText}>로그인</Text>
      </Pressable>
    </SafeAreaView>
  );
}
